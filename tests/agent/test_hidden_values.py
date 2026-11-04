import hashlib
import json

from test_gateway import gateway, mf_executable  # noqa: F401

from agent.evaluation.hidden_values import hidden_value_cases, seal_hidden_values
from agent.gateway import Gateway


def test_sealed_hidden_values_are_read_from_the_modified_snapshot(gateway, tmp_path, mf_executable):
    baseline = gateway._db.parent
    bundle_path = baseline / "bundle.json"
    original = bundle_path.read_bytes()
    original_db = hashlib.sha256(gateway._db.read_bytes()).hexdigest()
    root = tmp_path / "qualification"
    bundle = seal_hidden_values(baseline, root, mf_executable)
    hidden = Gateway(root, mf_executable, release_id=bundle.name)
    validation = json.loads((bundle / "validation.json").read_text())
    assert validation["synthetic_qualification_only"] is True
    assert validation["base_database_sha256"] == original_db
    assert hidden._db_hash != original_db
    assert hidden._manifest_hash == gateway._manifest_hash
    assert not (root / "environments").exists()
    catalog = json.dumps(hidden.get_catalog())
    for amount in ("987654.23", "493.46", "123456.78", "234567.89", "1234.57", "-741.11"):
        assert amount not in catalog

    for case in hidden_value_cases():
        result = hidden.query_metrics(case.intent)
        case.check(result)
        assert result.provenance.bundle_sha256 != gateway._bundle_hash
        assert result.provenance.release_id == bundle.name
        assert result.provenance.source_revision is None

    assert bundle_path.read_bytes() == original
    assert hashlib.sha256(gateway._db.read_bytes()).hexdigest() == original_db
