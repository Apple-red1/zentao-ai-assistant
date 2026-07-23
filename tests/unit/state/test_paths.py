from zentao_ai.state import default_ledger_path


def test_default_database_is_not_in_repository(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    path = default_ledger_path()
    assert path.name == "run-ledger.sqlite3"
    assert tmp_path not in path.parents
    assert "zentao-ai-assistant" in str(path)
