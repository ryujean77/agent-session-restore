#!/usr/bin/env python3
"""w — 이름 하나로 Claude Code / Codex / AGY 세션을 열고, 다시 열면 그 세션으로 이어 붙는다.

  w <name> [claude|codex|agy]   열기(처음) 또는 이어받기(다음부터). 도구 기본값 claude
  w ls                          장부 보기
  w rm <name>                   장부에서 지우기 (대화 자체는 지우지 않음)
  w tasks [folder]              folder/.vscode/tasks.json 재생성 (VS Code 열면 전부 자동 복원)
  python w.py install [bindir]  'w' 명령 등록 (기본 ~/.local/bin, PATH 에 있어야 함)

장부: ~/.w-sessions.json   {name: {tool, cwd, id, started}}
Claude 는 백그라운드 세션(claude --bg)으로 돌리고 터미널은 attach 만 한다 → VS Code 를 꺼도 대화가 계속 돈다.
Codex·AGY 는 터미널 안에서 돌고, 다음에 열 때 세션 ID 로 이어받는다.
"""
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
REG = Path(os.environ.get("W_REGISTRY", HOME / ".w-sessions.json"))
TOOLS = ("claude", "codex", "agy")
TASK_PREFIX = "w: "


def load():
    try:
        return json.loads(REG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def put(name, entry):
    # 20개 터미널이 동시에 뜰 때를 위해 매번 다시 읽고 한 항목만 바꿔 원자적으로 쓴다.
    # ponytail: 파일 잠금 없음, 같은 순간 두 새 세션이 겹치면 한쪽 기록이 빠질 수 있다 → w ls 로 확인
    reg = load()
    if entry is None:
        reg.pop(name, None)
    else:
        reg[name] = entry
    tmp = REG.with_suffix(".tmp")
    tmp.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, REG)


def exe(tool):
    path = shutil.which(tool)
    if not path:
        sys.exit(f"'{tool}' 명령을 찾을 수 없습니다. 설치·PATH 를 확인하세요.")
    return path


def norm(p):
    return os.path.normcase(os.path.abspath(str(p).removeprefix("\\\\?\\")))


# ---------- Claude: 백그라운드 세션 + attach ----------

def claude_live():
    out = subprocess.run([exe("claude"), "agents", "--json"], capture_output=True,
                         text=True, encoding="utf-8", errors="replace").stdout
    try:
        return [a for a in json.loads(out) if a.get("kind") == "background"]
    except ValueError:
        return []


def run_claude(name, e):
    cl = exe("claude")
    live = next((a for a in claude_live() if a.get("sessionId") == e.get("id")), None) if e.get("id") else None
    if not live:
        # 이어받을 때는 플래그를 붙이지 않는다: 붙이면 claude 가 같은 세션 대신 복사본을 새로 만든다
        args = [cl, "--bg", "--resume", e["id"]] if e.get("id") else [cl, "--bg", "-n", name]
        out = subprocess.run(args, cwd=e["cwd"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace").stdout
        m = re.search(r"backgrounded\W+([0-9a-f]{8})", out)
        if not m:
            sys.exit("claude --bg 실행 결과를 읽지 못했습니다:\n" + out)
        live = next((a for a in claude_live() if a.get("id") == m.group(1)), {"id": m.group(1)})
        if live.get("sessionId") and live["sessionId"] != e.get("id"):
            e["id"] = live["sessionId"]
            put(name, e)
    return subprocess.call([cl, "attach", live["id"]], cwd=e["cwd"])


# ---------- Codex / AGY: 터미널 안에서 실행, 다음에 ID 로 이어받기 ----------

def capture_codex(e, claimed):
    dbs = sorted((HOME / ".codex").glob("state_*.sqlite"))
    if not dbs:
        return None
    con = sqlite3.connect(f"file:{dbs[-1]}?mode=ro", uri=True)
    rows = con.execute("select id, cwd from threads where source = 'cli' and created_at >= ? "
                       "order by created_at", (int(e["started"]) - 2,)).fetchall()
    con.close()
    return next((i for i, c in rows if i not in claimed and norm(c) == norm(e["cwd"])), None)


def capture_agy(e, claimed):
    convs = HOME / ".gemini" / "antigravity-cli" / "conversations"
    found = sorted((f.stat().st_ctime, f.stem) for f in convs.glob("*.db")
                   if f.stat().st_ctime >= e["started"] - 2 and f.stem not in claimed)
    return found[0][1] if found else None


CAPTURE = {"codex": capture_codex, "agy": capture_agy}


def capture(name, e):
    """새로 연 Codex·AGY 세션의 ID 를 '연 시각 이후 처음 생긴, 아직 주인 없는 대화'로 찾아 적는다."""
    if e.get("id") or e["tool"] not in CAPTURE:
        return e
    claimed = {v.get("id") for v in load().values()}
    # ponytail: 같은 폴더에서 같은 초에 새 세션을 두 개 열면 서로 바뀔 수 있다 → 새 세션은 하나씩 연다
    sid = CAPTURE[e["tool"]](e, claimed)
    if sid:
        e["id"] = sid
        put(name, e)
    return e


def run_cli(name, e):
    e = capture(name, e)
    if e.get("id"):
        cmd = [exe("codex"), "resume", e["id"]] if e["tool"] == "codex" else [exe("agy"), "--conversation", e["id"]]
    else:
        e["started"] = time.time()
        put(name, e)
        cmd = [exe(e["tool"])]
    code = subprocess.call(cmd, cwd=e["cwd"])
    capture(name, e)
    return code


# ---------- VS Code tasks.json ----------

def write_tasks(folder):
    folder = Path(folder)
    path = folder / ".vscode" / "tasks.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"version": "2.0.0", "tasks": []}
    except ValueError:
        print(f"[w] {path} 에 주석 등 JSON 이 아닌 내용이 있어 건드리지 않았습니다. 주석을 지우고 'w tasks' 를 다시 실행하세요.")
        return
    keep = [t for t in data.get("tasks", []) if not str(t.get("label", "")).startswith(TASK_PREFIX)]
    mine = [{
        "label": TASK_PREFIX + n,
        "type": "process",
        "command": sys.executable,
        "args": [str(Path(__file__).resolve()), n],
        "options": {"cwd": e["cwd"]},
        "runOptions": {"runOn": "folderOpen"},
        "presentation": {"panel": "dedicated", "reveal": "always", "focus": False, "echo": False},
        "problemMatcher": [],
    } for n, e in sorted(load().items()) if norm(e["cwd"]) == norm(folder)]
    data["tasks"] = keep + mine
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[w] {path}: 자동 복원 터미널 {len(mine)}개")


def install(bindir):
    """bindir 에 'w' 실행 파일을 만든다. Windows .cmd 는 비ASCII 경로를 코드페이지에 따라 못 읽으므로
    ASCII 만 담은 .cmd 가 옆의 .py(UTF-8) 를 부르고, 그 .py 가 이 파일을 실행한다."""
    me = Path(__file__).resolve()
    bindir.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        (bindir / "w-run.py").write_text(
            f"import runpy\nrunpy.run_path({str(me)!r}, run_name='__main__')\n", encoding="utf-8")
        py = sys.executable if sys.executable.isascii() else "python"
        (bindir / "w.cmd").write_bytes(f'@"{py}" "%~dp0w-run.py" %*\r\n'.encode("ascii"))
        made = bindir / "w.cmd"
    sh = bindir / "w"  # macOS·Linux, 그리고 Windows 의 Git Bash 용
    sh.write_text(f'#!/bin/sh\nexec "{Path(sys.executable).as_posix()}" "{me.as_posix()}" "$@"\n', encoding="utf-8")
    sh.chmod(0o755)
    made = made if os.name == "nt" else sh
    on_path = any(norm(p) == norm(bindir) for p in os.environ.get("PATH", "").split(os.pathsep) if p)
    print(f"[w] {made} 생성" + ("" if on_path else f"\n[w] 주의: {bindir} 가 PATH 에 없습니다. PATH 에 추가하세요."))
    return 0


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd == "ls":
        reg = load()
        for n, e in sorted(reg.items()):
            capture(n, e)
        for n, e in sorted(load().items()):
            print(f"{n:20} {e['tool']:7} {(e.get('id') or '(첫 대화 전)')[:36]:36} {e['cwd']}")
        return 0
    if cmd == "rm" and len(argv) == 2:
        e = load().pop(argv[1], None)
        put(argv[1], None)
        if e:
            write_tasks(e["cwd"])
        return 0
    if cmd == "tasks":
        write_tasks(argv[1] if len(argv) > 1 else os.getcwd())
        return 0
    if cmd == "install":
        return install(Path(argv[1]) if len(argv) > 1 else HOME / ".local" / "bin")

    name, tool = cmd, (argv[1] if len(argv) > 1 else None)
    if tool and tool not in TOOLS:
        sys.exit(f"도구는 {', '.join(TOOLS)} 중 하나입니다.")
    e = load().get(name)
    if e is None:
        e = {"tool": tool or "claude", "cwd": os.getcwd(), "id": None, "started": time.time()}
        put(name, e)
        if (Path(e["cwd"]) / ".vscode").is_dir() or (Path(e["cwd"]) / ".git").exists():
            write_tasks(e["cwd"])
    elif tool and tool != e["tool"]:
        sys.exit(f"'{name}' 은 이미 {e['tool']} 세션입니다. 다른 이름을 쓰거나 'w rm {name}' 후 다시 여세요.")
    return run_claude(name, e) if e["tool"] == "claude" else run_cli(name, e)


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main(sys.argv[1:]))
