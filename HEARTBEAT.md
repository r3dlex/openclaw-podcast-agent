# HEARTBEAT.md

Podcaster periodic checks. On every heartbeat poll, run through these tasks
in order. If nothing needs attention after all checks, reply `HEARTBEAT_OK`.

## MQ Tasks (Inter-Agent Message Queue)

The MQ is the primary channel for agent-to-agent communication.
Service: `$IAMQ_HTTP_URL` (default `http://127.0.0.1:18790`).
Protocol: see `openclaw-inter-agent-message-queue/spec/PROTOCOL.md`.

- [x] **Send heartbeat** — keep yourself visible to other agents
  ```
  POST http://127.0.0.1:18790/heartbeat
  {"agent_id": "podcast_agent"}
  ```

- [x] **Check inbox** — process unread messages from other agents
  ```
  GET http://127.0.0.1:18790/inbox/podcast_agent?status=unread
  ```
  For each unread message:
  1. Mark as read: `PATCH /messages/{id} {"status": "read"}`
  2. If `type: "request"` — act on it (produce episode, preview voice, etc.)
  3. Reply through the MQ with `replyTo` threading:
     ```
     POST http://127.0.0.1:18790/send
     {
       "from": "podcast_agent",
       "to": "{requesting_agent}",
       "type": "response",
       "subject": "Re: {original_subject}",
       "body": "{your response}",
       "replyTo": "{original_message_id}"
     }
     ```
  4. Mark original as acted: `PATCH /messages/{id} {"status": "acted"}`

- [x] **Check broadcast** — read system-wide announcements
  Broadcast messages appear in your inbox alongside direct messages.
  Read them, acknowledge internally, mark as `read`.

## Pipeline Tasks

- [x] **Check for pending one-shot tasks** — review `spec/TASK.md`
- [x] **Check episode generation status** — if a long-running production
  is in progress, check if it completed or failed

## Report to User

After completing all checks above, **send a summary to the user via your messaging channel** (Telegram through OpenClaw gateway). The user cannot see IAMQ messages.

- If you processed production requests or episodes are in progress: summarize what happened.
  Example: "Heartbeat: episode '[title]' in production — TTS at 80%. Should be ready in ~3 min."
- If nothing happened: "No pending episodes. Standing by for production requests."
- TTS failures, LLM API timeouts, audio errors: report IMMEDIATELY, don't wait for the heartbeat summary.

## Rules

- MQ replies go through `POST /send` with `replyTo`
- Mark messages `read` immediately, `acted` after completing the request
- Keep heartbeat responses fast — batch checks, don't deep-dive on heartbeat
- If a production request will take time, reply with an acknowledgment first,
  then send the full response when ready
