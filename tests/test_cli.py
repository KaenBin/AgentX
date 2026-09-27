from src.agents.__main__ import main
from src.tools import db_queries as db


def test_cli_one_shot_and_session_cleanup(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(db, "DB", tmp_path / "cli.db")
    monkeypatch.setattr("sys.argv", ["agent", "--question", "missing receipt"])
    monkeypatch.setattr("getpass.getpass", lambda prompt: "LearnDemo2026!")
    assert main() == 0
    output = capsys.readouterr().out
    assert "retrieve_sources" in output
    assert "duplicate" in output
    with db.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM chats").fetchone()[0] == 1


def test_cli_rejects_bad_login(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(db, "DB", tmp_path / "cli.db")
    monkeypatch.setattr("sys.argv", ["agent", "--question", "missing receipt"])
    monkeypatch.setattr("getpass.getpass", lambda prompt: "bad")
    assert main() == 1
    assert "Incorrect username or password" in capsys.readouterr().out
