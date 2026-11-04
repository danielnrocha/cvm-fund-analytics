"""Private OAuth authorization and storage for the local analytics application."""
import argparse
import asyncio
import fcntl
import json
import logging
import os
import stat
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

from pydantic_ai.providers.openai_codex import OpenAICodexCredentials, OpenAICodexOAuthFlow


class AuthError(Exception):
    """A public error code safe for terminal output."""


def _application_data() -> Path:
    base = Path.home() / ("Library/Application Support" if sys.platform == "darwin" else ".local/share")
    return base / "dbt-demo-analytics-agent"


def _private(info: os.stat_result, kind, mode: int) -> bool:
    return kind(info.st_mode) and stat.S_IMODE(info.st_mode) == mode and info.st_uid == os.getuid()


class CredentialStore:
    def __init__(self, directory: Path | None = None):
        self.directory = directory if directory is not None else _application_data()
        self.path = self.directory / "codex-oauth.json"

    def _check_directory(self) -> None:
        if not _private(self.directory.lstat(), stat.S_ISDIR, 0o700):
            raise AuthError("credentials_invalid")

    def _read(self) -> OpenAICodexCredentials:
        try:
            self._check_directory()
            with os.fdopen(os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
                info = os.fstat(stream.fileno())
                if not _private(info, stat.S_ISREG, 0o600) or info.st_size > 65536:
                    raise AuthError("credentials_invalid")
                data = json.load(stream)
            keys = {"access_token", "refresh_token", "account_id"}
            if (not isinstance(data, dict) or data.keys() != keys
                    or any(not isinstance(value, str) or not value for value in data.values())):
                raise AuthError("credentials_invalid")
            return OpenAICodexCredentials(**data)
        except FileNotFoundError:
            raise AuthError("login_required") from None
        except (OSError, ValueError):
            raise AuthError("credentials_invalid") from None

    async def load(self) -> OpenAICodexCredentials:
        return self._read()

    async def save(self, credentials: OpenAICodexCredentials) -> None:
        temporary = None
        try:
            self._check_directory()
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.directory, suffix=".tmp", delete=False
            ) as stream:
                temporary = Path(stream.name)
                json.dump(asdict(credentials), stream)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(self.path)
            directory_fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            raise AuthError("credentials_write_failed") from None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def status(self) -> str:
        try:
            self._read()
        except AuthError as exc:
            return str(exc)
        return "credentials_present"

    @contextmanager
    def session(self):
        """Hold a process lock through provider load, refresh, and durable save."""
        fd = None
        try:
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            self._check_directory()
            fd = os.open(self.directory / "session.lock", os.O_CREAT | os.O_NOFOLLOW | os.O_RDWR, 0o600)
            if not _private(os.fstat(fd), stat.S_ISREG, 0o600):
                raise AuthError("credentials_invalid")
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise AuthError("auth_busy") from None
        except (OSError, AuthError) as exc:
            if fd is not None:
                os.close(fd)
            if isinstance(exc, AuthError):
                raise
            raise AuthError("credentials_invalid") from None
        try:
            yield
        finally:
            os.close(fd)


async def login(store: CredentialStore) -> None:
    with store.session():
        flow = OpenAICodexOAuthFlow()
        print(flow.authorization_url(), flush=True)
        async with asyncio.timeout(300):
            await store.save(await flow.exchange_code_from_callback())
    print("credentials_present", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("login", "status"))
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    store = CredentialStore()
    if args.command == "status":
        print(store.status())
        return 0
    # The documented OAuth exchange uses an ephemeral client. Clear ambient
    # proxy variables in this standalone login process before it is created.
    for name in tuple(os.environ):
        if name.lower().endswith("_proxy"):
            del os.environ[name]
    os.environ["NO_PROXY"] = "*"
    try:
        asyncio.run(login(store))
    except AuthError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (Exception, KeyboardInterrupt):
        print("oauth_login_failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
