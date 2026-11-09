---
name: agent-session-restore
description: >
  VS Code 터미널 여러 개(12~20개)에서 쓰는 Claude Code · Codex · AGY 세션에 이름을 붙여,
  VS Code 재실행·재부팅 뒤에도 고르지 않고 각자 자기 대화로 자동 복원한다(`w <이름>`).
  "터미널 세션 복원", "세션 날아감", "VS Code 재실행하면 세션 사라짐", "세션 이름 붙여서 열어줘",
  "w 명령", "named session", "restore agent terminals", "resume all sessions" 요청 시 활성화.
---

# agent-session-restore (`w`)

작업 전 같은 폴더의 `notes.md` 를 먼저 읽는다. 설치·사용 상세는 [README.md](README.md).

## 1. 개요
터미널마다 이름 하나로 세션을 연다. 장부 `~/.w-sessions.json` 에 이름→세션 ID 를 적고,
`.vscode/tasks.json` 에 이름마다 `runOn: folderOpen` 작업을 만들어 VS Code 를 열면 전부 다시 붙는다.
- Claude: `claude --bg` 백그라운드 세션 + `claude attach`. VS Code 를 꺼도 대화가 계속 돈다.
- Codex: `codex resume <ID>` / AGY: `agy --conversation <ID>`. ID 는 "연 시각 이후 그 폴더에서 처음 생긴 대화"로 자동 기록.

## 2. 사용 시점
사용자가 터미널 세션 유지·복원, 여러 에이전트 터미널을 이름으로 관리하길 원할 때.
claude-mem 같은 기억 플러그인과 다르다: 그쪽은 새 세션에 요약을 넣는 것이고, 이건 **같은 세션으로 돌아가는 것**이다. 혼동하는 요청이면 차이를 먼저 설명한다.

## 3. 사전 확인
- `python --version` (3.9+), `w --help` 로 설치 여부 확인. 없으면 README 의 설치 절차.
- VS Code 사용자 설정 `task.allowAutomaticTasks: "on"`, `terminal.integrated.persistentSessionReviveProcess: "never"`.
  사용자 설정 파일 수정은 사용자 확인을 받고 하며, 수정 전 백업한다.

## 4. 워크플로우
### Step 1: 설치 확인
`python scripts/test_w.py` → `OK test_w`. `w` 가 없으면 `python scripts/w.py install` (손으로 .cmd 를 쓰지 않는다: 한글 경로가 코드페이지에 따라 깨진다).
### Step 2: 이름 붙여 열기
사용자에게 안내: 작업 폴더에서 `w <이름> [claude|codex|agy] [메모…]` (도구가 아닌 단어는 메모로 저장). 이름이 귀찮으면 `w` / `w codex` / `w agy` 로 자동 번호(`claude-1` …). 새 이름은 한 번에 하나씩.
도구 이름(`claude`·`codex`·`agy`) 하나만 주면 자동 이름 모드이므로, 세션 이름을 도구 이름과 똑같이 지을 수는 없다.
### Step 3: 복원
VS Code 재실행 → `w: <이름>` 터미널 자동 실행. 수동으로는 `w <이름>`. 목록은 `w ls`, Claude 전체 상태는 `claude agents`.
### Step 4: 정리
`w rm <이름>` (대화는 남고 장부·tasks.json 에서만 빠짐).

## 5. 규칙
- 각 도구의 저장소(`~/.codex/state_*.sqlite`, `~/.gemini/antigravity-cli/conversations/`)는 **읽기 전용**으로만 연다.
- AGY 대화 폴더 내용을 아카이빙·색인하지 않는다(파일명=ID 만 쓴다).
- Claude 를 이어받을 때 `claude --bg --resume <ID>` 에 다른 플래그(`-n` 등)를 붙이지 않는다. 붙이면 복사본이 새로 생긴다.

## 6. 증명
1. `python scripts/test_w.py` 출력 `OK test_w`.
2. `w --help` 가 PowerShell 에서 도움말 첫 줄을 출력.
3. Claude 왕복: 새 이름 생성 → `claude stop <id>` → 다시 `w <이름>` 시 장부 ID 동일(2회 반복).
4. `w ls` 에서 Codex·AGY 이름이 첫 대화 후 ID 를 가짐(`(첫 대화 전)` 아님).
5. 작업 폴더 `.vscode/tasks.json` 의 `w:` 작업 수 = 그 폴더 장부 항목 수.
6. 테스트로 만든 백그라운드 세션은 `claude agents` 에서 0건(정리 완료).

## 7. 예시
```
w seo            # Claude 'seo' 시작 → 다음에 w seo 하면 같은 대화
w review codex   # Codex 'review'
w ls
```
