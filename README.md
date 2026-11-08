# agent-session-restore (`w`)

> 터미널 12~20개에 Claude Code · Codex · AGY(Antigravity CLI)를 띄워 쓰는데, VS Code를 재실행하면 전부 사라진다?
> 터미널마다 **이름** 하나만 붙이세요. 다시 열 때 고를 필요 없이 각자 자기 대화로 돌아옵니다.

*Name each AI-agent terminal once (`w seo`). Reopen VS Code and every named terminal comes back attached to its own Claude Code / Codex / AGY session — no picker, no copy-pasting IDs.*

## 무엇을 해 주나

| | Claude Code | Codex CLI | AGY (Antigravity CLI) |
|---|---|---|---|
| 처음 `w <이름>` | 백그라운드 세션 생성 후 화면 연결 | 새 세션 시작 | 새 세션 시작 |
| 다시 `w <이름>` | 같은 세션에 다시 연결 | `codex resume <ID>` | `agy --conversation <ID>` |
| VS Code를 꺼도 | **대화가 계속 돈다** (백그라운드) | 멈춤, 다음에 이어받기 | 멈춤, 다음에 이어받기 |
| 재부팅 후 | `w <이름>`이 같은 세션을 다시 띄움 | 이어받기 | 이어받기 |

- 이름과 세션 ID는 장부 `~/.w-sessions.json` 하나에 적힙니다.
- 새 이름을 만들 때마다 `.vscode/tasks.json`이 갱신되어, **VS Code를 열면 이름 붙은 터미널이 전부 자동으로 다시 열립니다.**
- 추가 토큰 소비 없음. 요약·기억 주입을 하지 않고, 각 도구의 원래 이어받기 기능만 씁니다. (이어받은 뒤 첫 질문 한 번만 캐시가 비어 평소보다 비쌉니다.)

## 설치

필요: Python 3.9+, 그리고 쓰는 도구(`claude` 백그라운드 세션을 지원하는 Claude Code, `codex`, `agy`) 중 하나 이상.

```bash
git clone https://github.com/ryujean77/agent-session-restore.git
```

`w` 명령을 등록합니다. (Windows·macOS·Linux 공통)

```bash
python agent-session-restore/scripts/w.py install          # 기본 ~/.local/bin 에 w 생성
python agent-session-restore/scripts/w.py install <폴더>   # 다른 폴더에 만들 때
```
- Windows 는 `w.cmd`(PowerShell·cmd 용)와 `w`(Git Bash 용)를, macOS·Linux 는 `w` 를 만듭니다.
- 폴더가 PATH 에 없으면 안내가 나옵니다. PATH 에 추가하고 터미널을 새로 여세요.
- 설치 경로에 한글 등 비ASCII 문자가 있어도 동작합니다(콘솔 코드페이지 949·65001 모두 확인).

**VS Code 설정** (`Ctrl+Shift+P` → *Preferences: Open User Settings (JSON)*) 에 두 줄 추가:
```jsonc
"task.allowAutomaticTasks": "on",                         // 폴더를 열 때 w 터미널 자동 실행 허용
"terminal.integrated.persistentSessionReviveProcess": "never" // 재실행 때 빈 셸 탭이 중복으로 살아나는 것 방지
```
(`terminal.integrated.enablePersistentSessions` 는 기본값 `true` 그대로 두세요. *Reload Window* 때는 터미널이 끊기지 않고 유지됩니다.)

설치 확인:
```bash
python agent-session-restore/scripts/test_w.py   # → OK test_w
w --help
```

## 사용법

```bash
cd ~/my-project            # 작업 폴더에서
w seo                      # Claude 세션 'seo' (도구 생략 시 claude)
w review codex             # Codex 세션 'review'
w draft agy                # AGY 세션 'draft'

w seo                      # 언제든 다시: 같은 대화로 연결
w ls                       # 이름 · 도구 · 세션 ID · 폴더 목록
w rm draft                 # 장부에서 제거 (대화 기록 자체는 남음)
w tasks                    # 현재 폴더의 .vscode/tasks.json 을 장부 기준으로 다시 생성
```

**하루 흐름**
1. 처음 한 번, 터미널마다 `w <이름>` 으로 엽니다.
2. VS Code 를 재실행하면 `w: <이름>` 터미널들이 자동으로 열리며 각자 이어집니다.
3. Claude 화면에서 빠져나와도(터미널 닫기 등) 세션은 백그라운드에서 계속 돕니다. `claude agents` 로 전체 상태를 볼 수 있습니다.

## 알아둘 점

- **Codex·AGY 의 세션 ID 는 "이름을 연 시각 이후 그 폴더에서 처음 생긴 대화"로 찾아 적습니다.** 새 이름은 한 번에 하나씩 여세요. 같은 폴더에서 같은 순간 두 개를 새로 열면 서로 바뀔 수 있습니다. 첫 메시지를 보내기 전에 닫으면 대화가 생기지 않으므로 다음에 다시 새로 시작합니다.
- Codex 는 `~/.codex/state_*.sqlite`, AGY 는 `~/.gemini/antigravity-cli/conversations/` 를 **읽기만** 합니다. 각 도구가 저장 구조를 바꾸면 ID 자동 기록이 멈출 수 있습니다(`w ls` 에 `(첫 대화 전)` 으로 남음).
- 기존 `.vscode/tasks.json` 의 다른 작업은 보존합니다. 단, 주석이 있는 파일은 손대지 않고 안내만 합니다.
- Claude 백그라운드 세션은 처음 연결했을 때 프로젝트 MCP 서버 허용 여부를 물을 수 있습니다. 한 번 답하면 됩니다.
- 장부는 잠금 없이 원자적 쓰기만 합니다. 동시에 20개가 떠도 기존 이름은 ID 가 이미 있어 쓰기가 일어나지 않습니다.

## AI 에이전트 스킬로 쓰기

`SKILL.md` 가 함께 들어 있습니다. Claude Code·Codex·AGY 의 스킬 폴더에 이 저장소를 두면, "터미널 세션 복원", "세션 이름 붙여서 열어줘" 같은 요청에 에이전트가 `w` 를 설치·사용합니다.

## License

MIT
