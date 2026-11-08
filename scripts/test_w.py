"""w.py 자체 점검: python test_w.py  (실제 장부·tasks.json 은 건드리지 않는다)"""
import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path

tmp = Path(tempfile.mkdtemp())
os.environ["W_REGISTRY"] = str(tmp / "reg.json")
import sys
sys.stdout.reconfigure(errors="replace")
import w  # noqa: E402

w.HOME = tmp
work = tmp / "proj"
(work / ".vscode").mkdir(parents=True)
t0 = time.time()

# 장부 쓰기/지우기
w.put("a", {"tool": "codex", "cwd": str(work), "id": None, "started": t0})
w.put("b", {"tool": "agy", "cwd": str(work), "id": None, "started": t0})
w.put("x", {"tool": "codex", "cwd": str(work), "id": "OLD", "started": 0})
assert set(w.load()) == {"a", "b", "x"}

# Codex: 연 시각 이후 cli 대화 중 주인 없는 첫 번째, exec·다른 폴더·이미 주인 있는 것은 제외
(tmp / ".codex").mkdir()
con = sqlite3.connect(tmp / ".codex" / "state_5.sqlite")
con.execute("create table threads (id text, created_at int, source text, cwd text)")
con.executemany("insert into threads values (?,?,?,?)", [
    ("OLD", int(t0) + 1, "cli", str(work)),
    ("EXEC", int(t0) + 1, "exec", str(work)),
    ("OTHER", int(t0) + 1, "cli", str(tmp)),
    ("NEW", int(t0) + 2, "cli", "\\\\?\\" + str(work)),
])
con.commit()
con.close()
assert w.capture("a", w.load()["a"])["id"] == "NEW", w.load()["a"]

# AGY: 연 시각 이후 생긴 대화 파일
conv = tmp / ".gemini" / "antigravity-cli" / "conversations"
conv.mkdir(parents=True)
(conv / "agy-123.db").write_bytes(b"")
assert w.capture("b", w.load()["b"])["id"] == "agy-123"

# tasks.json: 남의 작업은 보존, w 작업은 장부와 동일하게
tasks = work / ".vscode" / "tasks.json"
tasks.write_text(json.dumps({"version": "2.0.0", "tasks": [{"label": "build"}, {"label": "w: gone"}]}))
w.write_tasks(work)
labels = [t["label"] for t in json.loads(tasks.read_text(encoding="utf-8"))["tasks"]]
assert labels == ["build", "w: a", "w: b", "w: x"], labels
w.main(["rm", "x"])
labels = [t["label"] for t in json.loads(tasks.read_text(encoding="utf-8"))["tasks"]]
assert labels == ["build", "w: a", "w: b"], labels
assert all(t["runOptions"]["runOn"] == "folderOpen" for t in json.loads(tasks.read_text(encoding="utf-8"))["tasks"][1:])

# 주석 있는 tasks.json 은 건드리지 않는다
tasks.write_text("// my comment\n{}")
w.write_tasks(work)
assert tasks.read_text() == "// my comment\n{}"

# 이름 자동 지정: 'w', 'w codex' → 비어 있는 가장 작은 번호
w.run_claude = w.run_cli = lambda name, e: 0
os.chdir(work)
w.put("codex-1", {"tool": "codex", "cwd": str(work), "id": "C1", "started": 0})
w.main(["codex"])
w.main([])
reg = w.load()
assert reg["codex-2"]["tool"] == "codex" and reg["claude-1"]["tool"] == "claude", sorted(reg)

print("OK test_w")
