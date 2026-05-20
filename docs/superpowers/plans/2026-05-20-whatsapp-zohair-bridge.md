# WhatsApp ↔ Zohair Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Read Shaun's 1:1 WhatsApp thread with Zohair inside Claude Code and send repo-context-grounded replies he approves first, restricted to the Zohair conversation only.

**Architecture:** Vendor `lharries/whatsapp-mcp` (MIT) into `tools/whatsapp-mcp/`. It is two local processes — a Go `whatsmeow` bridge (QR-linked to WhatsApp, persists messages to SQLite) and a Python MCP server Claude Code connects to. We add two defense-in-depth guards: a **storage allowlist** in the Go bridge (only Zohair's chat is written to disk) and a **recipient allowlist** in the Python `send_message` (refuses to message anyone but Zohair). The matchmaking-topic filter and draft-then-confirm sending are workflow conventions, not code.

**Tech Stack:** Go (whatsmeow), Python 3.11+ + `uv` + FastMCP, SQLite, Claude Code MCP.

**Spec:** `docs/superpowers/specs/2026-05-20-whatsapp-zohair-bridge-design.md`

**Path note (refines spec):** clone root is `tools/whatsapp-mcp/` (not `tools/whatsapp-bridge/`) because upstream already contains a `whatsapp-bridge/` subdir — using `tools/whatsapp-mcp/` avoids `whatsapp-bridge/whatsapp-bridge/` double-nesting. Env var name is `WHATSAPP_ALLOWED_JIDS` (the spec's conceptual `ZOHAIR_JID`); it is a comma-separated allowlist currently holding only Zohair.

---

## File Structure

| Path | Responsibility |
|---|---|
| `tools/whatsapp-mcp/` | Vendored upstream repo (nested `.git` removed) |
| `tools/whatsapp-mcp/whatsapp-bridge/main.go` | Go bridge — **patched** with storage allowlist |
| `tools/whatsapp-mcp/whatsapp-bridge/allowlist_test.go` | **New** — Go unit tests for the allowlist helpers |
| `tools/whatsapp-mcp/whatsapp-bridge/store/` | SQLite DB + session creds — **gitignored** |
| `tools/whatsapp-mcp/whatsapp-mcp-server/main.py` | Python MCP server — **patched** to load `.env` + enforce recipient guard |
| `tools/whatsapp-mcp/whatsapp-mcp-server/recipient_guard.py` | **New** — recipient allowlist helper |
| `tools/whatsapp-mcp/whatsapp-mcp-server/test_recipient_guard.py` | **New** — pytest for the guard |
| `tools/whatsapp-mcp/.env` | `WHATSAPP_ALLOWED_JIDS` — **gitignored** |
| `tools/whatsapp-mcp/.env.example` | Documents the variable, no value |
| `tools/whatsapp-mcp/run-bridge.sh` | **New** — sources `.env`, runs the Go bridge |
| `.mcp.json` | **New** — registers the MCP server with Claude Code (no secrets) |
| `.gitignore` | Append bridge secret/data paths |

---

## Task 1: Vendor the upstream repo + secret hygiene

**Files:**
- Create: `tools/whatsapp-mcp/` (cloned)
- Modify: `.gitignore`
- Create: `tools/whatsapp-mcp/.env`, `tools/whatsapp-mcp/.env.example`

- [ ] **Step 1: Verify prerequisites**

Run:
```bash
go version && uv --version
```
Expected: both print versions. If `go` missing: `brew install go`. If `uv` missing: `brew install uv`.

- [ ] **Step 2: Clone upstream and de-git it**

Run:
```bash
cd /Users/kanyuchi/Developer/Proof_Of_Talk_CD
mkdir -p tools
git clone https://github.com/lharries/whatsapp-mcp.git tools/whatsapp-mcp
rm -rf tools/whatsapp-mcp/.git
ls tools/whatsapp-mcp
```
Expected: lists `whatsapp-bridge/` and `whatsapp-mcp-server/` (vendored into our repo, no nested git).

- [ ] **Step 3: Add gitignore entries BEFORE creating any secrets**

Append to `.gitignore`:
```gitignore

# WhatsApp Zohair bridge — never commit credentials or message data
tools/whatsapp-mcp/whatsapp-bridge/store/
tools/whatsapp-mcp/.env
tools/whatsapp-mcp/**/*.db
tools/whatsapp-mcp/**/*.db-journal
```

- [ ] **Step 4: Create the gitignored `.env` and the committable `.env.example`**

Create `tools/whatsapp-mcp/.env`:
```dotenv
# Comma-separated WhatsApp JID allowlist. Only these chats are stored/sendable.
WHATSAPP_ALLOWED_JIDS=491732532061@s.whatsapp.net
```

Create `tools/whatsapp-mcp/.env.example`:
```dotenv
# Comma-separated WhatsApp JID allowlist (e.g. 491732532061@s.whatsapp.net).
# Only these chats are persisted by the Go bridge and sendable by the MCP server.
WHATSAPP_ALLOWED_JIDS=
```

- [ ] **Step 5: Verify `.env` is ignored, `.env.example` is not**

Run:
```bash
git check-ignore tools/whatsapp-mcp/.env && git status --porcelain tools/whatsapp-mcp/.env.example
```
Expected: first line prints the `.env` path (ignored); second shows `?? tools/whatsapp-mcp/.env.example` (tracked-to-be). If `.env` is NOT ignored, stop and fix `.gitignore` before continuing.

- [ ] **Step 6: Commit the vendored tree (without secrets)**

Run:
```bash
git add .gitignore tools/whatsapp-mcp/.env.example
git add tools/whatsapp-mcp/whatsapp-bridge tools/whatsapp-mcp/whatsapp-mcp-server tools/whatsapp-mcp/*.md 2>/dev/null
git status --porcelain | grep -c whatsapp-mcp/.env$ | grep -q '^0$' && echo "OK: .env not staged" || { echo "ABORT: .env is staged"; exit 1; }
git commit -m "chore(whatsapp): vendor lharries/whatsapp-mcp for Zohair bridge"
```
Expected: commit succeeds; "OK: .env not staged" printed.

---

## Task 2: Go storage allowlist (TDD)

**Files:**
- Create: `tools/whatsapp-mcp/whatsapp-bridge/allowlist_test.go`
- Modify: `tools/whatsapp-mcp/whatsapp-bridge/main.go` (add helpers; guards in `handleMessage` ~L414 and `handleHistorySync` ~L1018; `loadAllowedChatJIDs()` call in `main()` ~L789)

- [ ] **Step 1: Write the failing Go test**

Create `tools/whatsapp-mcp/whatsapp-bridge/allowlist_test.go`:
```go
package main

import (
	"os"
	"testing"
)

func TestChatUserPart(t *testing.T) {
	cases := map[string]string{
		"491732532061@s.whatsapp.net":    "491732532061",
		"491732532061:12@s.whatsapp.net": "491732532061",
		"491732532061":                   "491732532061",
		"123-456@g.us":                   "123-456",
	}
	for in, want := range cases {
		if got := chatUserPart(in); got != want {
			t.Errorf("chatUserPart(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestIsAllowedChat(t *testing.T) {
	os.Unsetenv("WHATSAPP_ALLOWED_JIDS")
	loadAllowedChatJIDs()
	if !isAllowedChat("000@s.whatsapp.net") {
		t.Error("expected allow-all when WHATSAPP_ALLOWED_JIDS unset")
	}

	os.Setenv("WHATSAPP_ALLOWED_JIDS", "491732532061@s.whatsapp.net")
	loadAllowedChatJIDs()
	if !isAllowedChat("491732532061@s.whatsapp.net") {
		t.Error("expected Zohair allowed")
	}
	if !isAllowedChat("491732532061:3@s.whatsapp.net") {
		t.Error("expected Zohair allowed with device suffix")
	}
	if isAllowedChat("999999@s.whatsapp.net") {
		t.Error("expected non-allowlisted chat blocked")
	}
}
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
cd tools/whatsapp-mcp/whatsapp-bridge && go test ./... 2>&1 | head -20
```
Expected: FAIL — `undefined: chatUserPart`, `undefined: loadAllowedChatJIDs`, `undefined: isAllowedChat`.

- [ ] **Step 3: Add the allowlist helpers to main.go**

Insert this block in `tools/whatsapp-mcp/whatsapp-bridge/main.go` immediately above `func handleMessage(` (~line 412):
```go
// allowedChatJIDs holds the user-part of each allowlisted JID. nil = allow all.
var allowedChatJIDs map[string]bool

// loadAllowedChatJIDs reads WHATSAPP_ALLOWED_JIDS (comma-separated) into allowedChatJIDs.
// Empty/unset keeps upstream allow-all behavior.
func loadAllowedChatJIDs() {
	raw := strings.TrimSpace(os.Getenv("WHATSAPP_ALLOWED_JIDS"))
	if raw == "" {
		allowedChatJIDs = nil
		return
	}
	set := make(map[string]bool)
	for _, j := range strings.Split(raw, ",") {
		if j = strings.TrimSpace(j); j != "" {
			set[chatUserPart(j)] = true
		}
	}
	allowedChatJIDs = set
}

// chatUserPart returns the bare user/number portion of a JID (before @ and any :device suffix).
func chatUserPart(jid string) string {
	if i := strings.IndexByte(jid, '@'); i >= 0 {
		jid = jid[:i]
	}
	if i := strings.IndexByte(jid, ':'); i >= 0 {
		jid = jid[:i]
	}
	return jid
}

// isAllowedChat reports whether messages from chatJID should be persisted.
func isAllowedChat(chatJID string) bool {
	if allowedChatJIDs == nil {
		return true
	}
	return allowedChatJIDs[chatUserPart(chatJID)]
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
cd tools/whatsapp-mcp/whatsapp-bridge && go test ./... 2>&1 | head -20
```
Expected: PASS (`ok` line).

- [ ] **Step 5: Wire the guard into the live-message path**

In `handleMessage`, the body starts (~line 413-414):
```go
	// Save message to database
	chatJID := msg.Info.Chat.String()
```
Insert directly AFTER that `chatJID :=` line:
```go
	if !isAllowedChat(chatJID) {
		return
	}
```

- [ ] **Step 6: Wire the guard into the history-sync path**

In `handleHistorySync`, inside the `for _, conversation := range ...` loop, after (~line 1018):
```go
		chatJID := *conversation.ID
```
Insert directly AFTER that line:
```go
		if !isAllowedChat(chatJID) {
			continue
		}
```

- [ ] **Step 7: Call the loader once at startup**

In `func main()` (~line 789), add this line near the top of the function body (after the logger is created, before the client connects):
```go
	loadAllowedChatJIDs()
```

- [ ] **Step 8: Verify the bridge still builds**

Run:
```bash
cd tools/whatsapp-mcp/whatsapp-bridge && go build ./... && go test ./... 2>&1 | tail -3
```
Expected: build succeeds (no output from build), tests `ok`.

- [ ] **Step 9: Commit**

Run:
```bash
cd /Users/kanyuchi/Developer/Proof_Of_Talk_CD
git add tools/whatsapp-mcp/whatsapp-bridge/main.go tools/whatsapp-mcp/whatsapp-bridge/allowlist_test.go
git commit -m "feat(whatsapp): storage allowlist — only persist allowlisted chats"
```

---

## Task 3: Bridge run script

**Files:**
- Create: `tools/whatsapp-mcp/run-bridge.sh`

- [ ] **Step 1: Create the run script**

Create `tools/whatsapp-mcp/run-bridge.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# Load the gitignored allowlist into the environment for the Go bridge.
set -a
[ -f .env ] && source .env
set +a
cd whatsapp-bridge
exec go run main.go
```

- [ ] **Step 2: Make it executable**

Run:
```bash
chmod +x tools/whatsapp-mcp/run-bridge.sh
```

- [ ] **Step 3: Verify it loads the env var (dry check, no WhatsApp connection)**

Run:
```bash
cd /Users/kanyuchi/Developer/Proof_Of_Talk_CD/tools/whatsapp-mcp
set -a; source .env; set +a; echo "ALLOWLIST=$WHATSAPP_ALLOWED_JIDS"
```
Expected: `ALLOWLIST=491732532061@s.whatsapp.net`.

- [ ] **Step 4: Commit**

Run:
```bash
cd /Users/kanyuchi/Developer/Proof_Of_Talk_CD
git add tools/whatsapp-mcp/run-bridge.sh
git commit -m "chore(whatsapp): add run-bridge.sh that sources the allowlist .env"
```

---

## Task 4: Python recipient allowlist (TDD)

**Files:**
- Create: `tools/whatsapp-mcp/whatsapp-mcp-server/recipient_guard.py`
- Create: `tools/whatsapp-mcp/whatsapp-mcp-server/test_recipient_guard.py`
- Modify: `tools/whatsapp-mcp/whatsapp-mcp-server/main.py` (load `.env`; guard in `send_message` ~L158)

- [ ] **Step 1: Add dev/runtime deps**

Run:
```bash
cd tools/whatsapp-mcp/whatsapp-mcp-server
uv add python-dotenv
uv add --dev pytest
```
Expected: `pyproject.toml` updated, lockfile resolved.

- [ ] **Step 2: Write the failing test**

Create `tools/whatsapp-mcp/whatsapp-mcp-server/test_recipient_guard.py`:
```python
import recipient_guard


def test_no_restriction_when_unset(monkeypatch):
    monkeypatch.delenv("WHATSAPP_ALLOWED_JIDS", raising=False)
    assert recipient_guard.is_allowed_recipient("999999")


def test_allows_listed_in_both_forms(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ALLOWED_JIDS", "491732532061@s.whatsapp.net")
    assert recipient_guard.is_allowed_recipient("491732532061")
    assert recipient_guard.is_allowed_recipient("491732532061@s.whatsapp.net")


def test_blocks_unlisted(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ALLOWED_JIDS", "491732532061@s.whatsapp.net")
    assert not recipient_guard.is_allowed_recipient("999999")
    assert not recipient_guard.is_allowed_recipient("999999@s.whatsapp.net")
```

- [ ] **Step 3: Run the test to verify it fails**

Run:
```bash
cd tools/whatsapp-mcp/whatsapp-mcp-server && uv run pytest test_recipient_guard.py -v 2>&1 | tail -15
```
Expected: FAIL — `ModuleNotFoundError: No module named 'recipient_guard'`.

- [ ] **Step 4: Implement the guard**

Create `tools/whatsapp-mcp/whatsapp-mcp-server/recipient_guard.py`:
```python
import os
from typing import Optional


def _user_part(recipient: str) -> str:
    r = recipient.strip()
    if "@" in r:
        r = r.split("@", 1)[0]
    if ":" in r:
        r = r.split(":", 1)[0]
    return r


def allowed_recipients() -> Optional[set]:
    raw = os.getenv("WHATSAPP_ALLOWED_JIDS", "").strip()
    if not raw:
        return None  # no restriction
    return {_user_part(j) for j in raw.split(",") if j.strip()}


def is_allowed_recipient(recipient: str) -> bool:
    allowed = allowed_recipients()
    if allowed is None:
        return True
    return _user_part(recipient) in allowed
```

- [ ] **Step 5: Run the test to verify it passes**

Run:
```bash
cd tools/whatsapp-mcp/whatsapp-mcp-server && uv run pytest test_recipient_guard.py -v 2>&1 | tail -10
```
Expected: 3 passed.

- [ ] **Step 6: Load `.env` at MCP server startup**

At the top of `tools/whatsapp-mcp/whatsapp-mcp-server/main.py`, after the existing imports, add:
```python
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
```

- [ ] **Step 7: Enforce the guard in `send_message`**

In `main.py`, `send_message` (~line 158) currently begins:
```python
def send_message(
    recipient: str,
    message: str
) -> Dict[str, Any]:
```
After the existing empty-recipient check (the `if not recipient:` block ~line 173), and BEFORE the `whatsapp_send_message(...)` call (~line 180), insert:
```python
    from recipient_guard import is_allowed_recipient
    if not is_allowed_recipient(recipient):
        return {
            "success": False,
            "message": f"Refused: {recipient} is not in WHATSAPP_ALLOWED_JIDS.",
        }
```

- [ ] **Step 8: Commit**

Run:
```bash
cd /Users/kanyuchi/Developer/Proof_Of_Talk_CD
git add tools/whatsapp-mcp/whatsapp-mcp-server/recipient_guard.py \
        tools/whatsapp-mcp/whatsapp-mcp-server/test_recipient_guard.py \
        tools/whatsapp-mcp/whatsapp-mcp-server/main.py \
        tools/whatsapp-mcp/whatsapp-mcp-server/pyproject.toml \
        tools/whatsapp-mcp/whatsapp-mcp-server/uv.lock
git commit -m "feat(whatsapp): recipient allowlist guard on send_message"
```

---

## Task 5: Register the MCP server with Claude Code

**Files:**
- Create: `.mcp.json`

- [ ] **Step 1: Create the project MCP config**

Create `.mcp.json` at the repo root:
```json
{
  "mcpServers": {
    "whatsapp": {
      "command": "uv",
      "args": [
        "--directory",
        "tools/whatsapp-mcp/whatsapp-mcp-server",
        "run",
        "main.py"
      ]
    }
  }
}
```
(No secrets here — the JID is loaded by the server from the gitignored `.env`. If `uv` is not on PATH for the Claude Code launch environment, replace `"uv"` with the output of `which uv`.)

- [ ] **Step 2: Verify JSON validity**

Run:
```bash
cd /Users/kanyuchi/Developer/Proof_Of_Talk_CD && python3 -c "import json; json.load(open('.mcp.json')); print('valid')"
```
Expected: `valid`.

- [ ] **Step 3: Commit**

Run:
```bash
git add .mcp.json
git commit -m "chore(whatsapp): register whatsapp MCP server in .mcp.json"
```

- [ ] **Step 4: Restart Claude Code to load the MCP server**

Manual: quit and reopen the Claude Code session (or run `/mcp` to confirm). After reload, the `whatsapp` server with its tools (`list_messages`, `send_message`, etc.) should be listed. Approve the project MCP server if prompted.

---

## Task 6: First-run authentication (manual, one-time)

No files. ~20-day session.

- [ ] **Step 1: Start the bridge**

Run (leave running in its own terminal):
```bash
/Users/kanyuchi/Developer/Proof_Of_Talk_CD/tools/whatsapp-mcp/run-bridge.sh
```
Expected: a QR code renders in the terminal. First build may take a minute while Go fetches deps.

- [ ] **Step 2: Link the device**

On the phone: WhatsApp → Settings → Linked Devices → Link a Device → scan the terminal QR.
Expected: bridge logs a successful connection and begins a history sync.

- [ ] **Step 3: Confirm the allowlist took effect during history sync**

Run (in another terminal):
```bash
cd /Users/kanyuchi/Developer/Proof_Of_Talk_CD/tools/whatsapp-mcp/whatsapp-bridge
sqlite3 store/messages.db "SELECT DISTINCT chat_jid FROM messages;"
```
Expected: only Zohair's JID (`491732532061@s.whatsapp.net`) appears. If other JIDs appear, the guard wiring in Task 2 is wrong — fix before proceeding.

---

## Task 7: End-to-end smoke verification

No files — verifies the whole chain.

- [ ] **Step 1: Storage allowlist (negative case)**

Have someone other than Zohair message you (or send yourself a note in a different chat). Then run:
```bash
cd /Users/kanyuchi/Developer/Proof_Of_Talk_CD/tools/whatsapp-mcp/whatsapp-bridge
sqlite3 store/messages.db "SELECT DISTINCT chat_jid FROM messages;"
```
Expected: the other chat's JID is **absent** — still only Zohair.

- [ ] **Step 2: Read path (via Claude Code)**

In Claude Code: ask "list the latest messages from Zohair." Claude calls the `list_messages` / `get_direct_chat_by_contact` MCP tool.
Expected: the Zohair thread is returned.

- [ ] **Step 3: Context-grounded draft**

In Claude Code: "Draft a reply to Zohair's last matchmaking question using the current project state."
Expected: a draft that references real facts from `project_state.md` / the codebase.

- [ ] **Step 4: Recipient guard (negative case)**

In Claude Code: ask Claude to call `send_message` with recipient `999999` and any text (a deliberate wrong-number test).
Expected: tool returns `Refused: 999999 is not in WHATSAPP_ALLOWED_JIDS.` — nothing sent.

- [ ] **Step 5: Send path (positive case, draft-then-confirm)**

In Claude Code: approve sending the Task-7-Step-3 draft to Zohair. Claude calls `send_message` (you also approve the MCP permission prompt).
Expected: the message arrives on Zohair's WhatsApp.

---

## Task 8: Living docs + final commit

**Files:**
- Modify: `session_log.md` (append), `whats_next.md` (own item only)

- [ ] **Step 1: Append a topic-tagged session-log entry**

Append to `session_log.md` (append-only; tag with `[whatsapp-bridge]` so it can't be confused with the concurrent email-activation session):
```markdown

## 2026-05-20 — [whatsapp-bridge] Two-way WhatsApp↔Zohair bridge shipped

- Vendored lharries/whatsapp-mcp into `tools/whatsapp-mcp/` (Go whatsmeow bridge + Python MCP server), nested `.git` removed.
- Storage allowlist patch (`isAllowedChat`) in `handleMessage` + `handleHistorySync` so only Zohair's chat (`WHATSAPP_ALLOWED_JIDS`) is written to SQLite; Go unit tests in `allowlist_test.go`.
- Recipient allowlist guard on the Python `send_message` (`recipient_guard.py` + pytest) so we can never message a non-allowlisted number.
- Registered via `.mcp.json`; creds/messages gitignored under `tools/whatsapp-mcp/store/` + `.env`.
- Workflow: read Zohair thread → semantic matchmaking-topic filter → repo-grounded draft → draft-then-confirm send. Smoke-tested end-to-end (QR auth, allowlist negative case, read, guard refusal, live send).
```

- [ ] **Step 2: Move the whats_next.md item to Done**

In `whats_next.md`, add a single new line under the **Done** section only. Do NOT touch the Now section or any other session's items — the email-activation session is live in parallel ([[concurrent-sessions-living-docs]]):
```markdown
- ✅ **WhatsApp↔Zohair bridge (2026-05-20)** — two-way, Zohair-only, draft-then-confirm; vendored whatsapp-mcp under `tools/whatsapp-mcp/`.
```

- [ ] **Step 3: Commit docs**

Run:
```bash
cd /Users/kanyuchi/Developer/Proof_Of_Talk_CD
git add session_log.md whats_next.md
git commit -m "docs(whatsapp): log Zohair bridge in living docs"
```

---

## Self-Review

**Spec coverage:**
- Read Zohair thread in Claude Code → Tasks 5, 7.2 (MCP `list_messages`).
- Send replies from Claude Code → Tasks 4, 7.5 (`send_message`).
- Restrict storage to Zohair only → Task 2 (Go allowlist), verified 6.3 / 7.1.
- Matchmaking-topic filter (semantic) → workflow convention, exercised 7.3 (not code, per spec).
- Repo-grounded drafting → Task 7.3.
- Draft-then-confirm send → Task 7.5 + MCP permission prompt.
- Privacy / never-commit creds → Tasks 1.3–1.6, gitignore verified 1.5.
- Local-only, deploy-excluded → lives under `tools/`, no deploy wiring touched.
- Personal-number QR auth → Task 6.

**Placeholder scan:** none — every code/edit step includes literal content and insertion anchors with approximate line numbers plus the surrounding code to locate them.

**Type/name consistency:** `chatUserPart`, `loadAllowedChatJIDs`, `isAllowedChat`, `allowedChatJIDs` (Go) and `_user_part`, `allowed_recipients`, `is_allowed_recipient` (Python) are used consistently across their definition, tests, and call sites. Env var `WHATSAPP_ALLOWED_JIDS` is identical in the Go bridge, `.env`, `.env.example`, `run-bridge.sh`, and the Python guard.
