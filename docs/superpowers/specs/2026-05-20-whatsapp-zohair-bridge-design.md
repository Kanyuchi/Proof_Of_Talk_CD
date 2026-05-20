# WhatsApp ↔ Zohair Bridge — Design Spec

**Date:** 2026-05-20
**Status:** Approved (design) — pending implementation plan
**Owner:** Shaun

## Goal

Let Shaun read his 1:1 WhatsApp thread with Zohair from inside Claude Code, and draft
context-rich replies (grounded in the matchmaking-app codebase) that he approves before
sending — all without leaving Claude Code. The driver is the imminent matchmaking-app
launch: Zohair asks product questions over WhatsApp, and replies are stronger when grounded
in the actual project state.

Zohair's number: **+491732532061** → JID `491732532061@s.whatsapp.net`.

## Requirements

### Functional
- Read incoming WhatsApp messages from the Zohair thread inside Claude Code.
- Send replies to Zohair from Claude Code (two-way).
- Restrict storage/access to the Zohair conversation only (no other chats stored).
- Surface only matchmaking-app-relevant messages from that thread (his thread mixes in
  unrelated personal topics).
- Draft replies grounded in this repo's context (project_state.md, session_log.md, code).

### Non-functional
- **Send safety:** draft-then-confirm. Nothing is sent to Zohair until Shaun explicitly
  approves the drafted text.
- **Privacy:** only the Zohair thread ever touches disk; credentials and message DB never
  committed.
- **Local-only:** a personal dev tool on Shaun's Mac, fully separate from the deployed
  Railway/Netlify app.
- **Personal number:** uses Shaun's existing WhatsApp account (the thread already exists),
  via an unofficial WhatsApp Web (linked-device) bridge.

## Out of scope (YAGNI)
- Group chats, media/voice-note handling, auto-send, any contact other than Zohair.
- Production deployment; always-on daemon / launchd service (started manually when needed).
- Official WhatsApp Business / Cloud API (rejected: would not attach to the existing
  personal thread).

## Approach

Reuse the open-source **`lharries/whatsapp-mcp`** (MIT) rather than building from scratch.
It is purpose-built for "let an MCP client read/respond to my WhatsApp," uses the reliable
`whatsmeow` library, and plugs into Claude Code as an MCP server. We add a thin Zohair
workflow layer plus one storage-level patch.

### Architecture

```
WhatsApp on phone ──QR link (≈20-day session)──┐
                                               │
(1) Go bridge (whatsmeow)                      │
    - links like WhatsApp Web                  ◄┘
    - receives messages → writes to local SQLite
    - ★ patch: JID allowlist — only persist Zohair's chat; drop all others
            │ store/messages.db
(2) Python MCP server
    - tools: list_messages, get_direct_chat_by_contact, get_last_interaction,
      send_message, search_contacts, get_message_context, …
            │ MCP (stdio)
Claude Code
    - reads Zohair thread via MCP tools
    - pulls matchmaking context from THIS repo
    - drafts reply → Shaun approves → send_message
```

### Components
- **Go bridge** (`tools/whatsapp-bridge/whatsapp-bridge/`): upstream, plus a JID-allowlist
  patch in the message handler so only `ZOHAIR_JID` messages are written to SQLite.
- **Python MCP server** (`tools/whatsapp-bridge/whatsapp-mcp-server/`): upstream, registered
  with Claude Code via repo `.mcp.json`.
- **Workflow layer** (no separate service): conventions Claude follows in-session —
  Zohair-only, semantic matchmaking-topic filtering, repo-grounded drafting, draft-then-confirm.

## Workflow rules
1. **Pin Zohair (storage-level allowlist).** `ZOHAIR_JID` in a gitignored `.env`; the Go
   bridge drops any message whose chat JID ≠ Zohair's. SQLite only ever holds the Zohair thread.
2. **Matchmaking-topic filter (semantic, read-time).** Claude reads the thread via
   `list_messages` and surfaces/acts on only matchmaking-app-relevant messages.
3. **Context-aware drafting.** Replies pull from this repo (project_state.md, session_log.md,
   code) so answers reflect what is actually shipped.
4. **Draft-then-confirm send.** Claude shows the drafted reply; only on Shaun's explicit "send"
   does it call `send_message`. As an MCP write tool, `send_message` also triggers Claude Code's
   permission prompt — two gates before anything reaches Zohair.

## Security & privacy
- Location: `tools/whatsapp-bridge/` inside this repo; **excluded from deploy**.
- **Never committed** (add to `.gitignore`):
  - `tools/whatsapp-bridge/store/` — SQLite message DB + whatsmeow session credentials.
  - `tools/whatsapp-bridge/.env` — holds `ZOHAIR_JID`.
  - `*.db`, `*.db-journal` under the bridge dir.
- `.env.example` documents `ZOHAIR_JID` with no real value (project convention).
- No secrets hardcoded.
- **Residual risk:** the linked-device session lets this machine read/send as Shaun on
  WhatsApp until unlinked. Mitigations: gitignored creds, draft-then-confirm, unlink anytime
  from phone (WhatsApp → Linked Devices). Unofficial bridges are against WhatsApp ToS with a
  small ban risk; acceptable at 1:1, human-paced volume.

## Setup & runtime
**One-time:** install Go, Python 3.11+, `uv` (ffmpeg optional, skip); clone whatsapp-mcp into
`tools/whatsapp-bridge/`; apply JID-allowlist patch; set `ZOHAIR_JID` in `.env`; add `.gitignore`
entries + `.env.example`; register the MCP server (`.mcp.json` / `claude mcp add`).
**Auth:** start Go bridge → scan QR with WhatsApp → Linked Devices (~20-day session, then re-scan).
**Daily:** bridge runs in a background terminal; in Claude Code: "what's new from Zohair?" →
read → draft → confirm → send.

## Verification (smoke tests)
| Piece | Test |
|---|---|
| Bridge auth | QR scan succeeds; bridge logs "connected" |
| JID allowlist | A message in a different chat is **absent** from SQLite; a Zohair message **is** stored |
| Read path | `list_messages` returns the Zohair thread in Claude Code |
| Draft + context | Claude drafts a reply citing real project state |
| Send path | Approved send arrives on Zohair's WhatsApp |

## Open questions
None — all design decisions resolved during brainstorming.
