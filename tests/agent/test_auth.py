import asyncio
import os
from stat import S_IMODE

import pytest
from pydantic_ai.providers.openai_codex import OpenAICodexCredentials

from agent.auth import AuthError, CredentialStore


def test_private_atomic_credentials_and_exclusive_session(tmp_path):
    store = CredentialStore(tmp_path / "private")
    credential = OpenAICodexCredentials(access_token="access", refresh_token="refresh", account_id="account")
    assert store.status() == "login_required"
    with store.session():
        asyncio.run(store.save(credential))
        assert asyncio.run(store.load()) == credential
        with pytest.raises(AuthError, match="auth_busy"):
            with store.session():
                pass
        assert S_IMODE(store.directory.stat().st_mode) == 0o700
        assert S_IMODE(store.path.stat().st_mode) == 0o600
        assert list(store.directory.glob("*.tmp")) == []
    assert store.status() == "credentials_present"
    os.chmod(store.path, 0o644)
    assert store.status() == "credentials_invalid"


def test_credentials_symlink_is_rejected(tmp_path):
    store = CredentialStore(tmp_path / "private")
    with store.session():
        store.path.symlink_to(tmp_path / "missing")
        assert store.status() == "credentials_invalid"
