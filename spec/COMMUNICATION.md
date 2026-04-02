# Inter-Agent Communication Protocol

The Podcaster agent communicates with peer agents via the Inter-Agent Message Queue (IAMQ) and direct file handoff to the Librarian.

## IAMQ Protocol

Service URL: `$IAMQ_HTTP_URL` (default `http://127.0.0.1:18790`).
Agent ID: `podcast_agent`.

### Registration

On scheduler startup, the agent registers with the IAMQ service. Registration is implicit via the first heartbeat.

### Heartbeat

Every 2 minutes, the scheduler sends:

```
POST $IAMQ_HTTP_URL/heartbeat
Content-Type: application/json

{"agent_id": "podcast_agent"}
```

This keeps the agent visible in `GET /agents` and signals liveness to peer agents.

### Inbox

Check for unread messages:

```
GET $IAMQ_HTTP_URL/inbox/podcast_agent?status=unread
```

Processing flow:
1. Mark as read: `PATCH /messages/{id}` with `{"status": "read"}`
2. If `type: "request"` — execute the requested action.
3. Reply via `POST /send` with `replyTo` threading.
4. Mark original as acted: `PATCH /messages/{id}` with `{"status": "acted"}`

### Sending Messages

```
POST $IAMQ_HTTP_URL/send
Content-Type: application/json

{
  "from": "podcast_agent",
  "to": "<target_agent_id>",
  "type": "request" | "response" | "info",
  "priority": "LOW" | "NORMAL" | "HIGH" | "URGENT",
  "subject": "Subject line",
  "body": "Message content",
  "replyTo": "<original_message_id>"  // optional, for threading
}
```

### Message Types

| Type | When |
|------|------|
| `request` | Asking another agent to do something |
| `response` | Replying to a request |
| `info` | Informational announcement (e.g., episode published) |

### Pipeline Announcements

Every completed pipeline automatically sends an announcement to the Librarian:

```json
{
  "from": "podcast_agent",
  "to": "librarian_agent",
  "type": "info",
  "priority": "NORMAL",
  "subject": "Episode published: <title>",
  "body": "Episode details, file paths, metadata..."
}
```

## Librarian Handoff Protocol

In addition to IAMQ announcements, the agent writes structured outputs to the Librarian workspace for archival indexing.

**Handoff directory:** `$LIBRARIAN_AGENT_WORKSPACE` (mounted at `/app/librarian_workspace` in Docker).

**Handoff flow:**
1. Pipeline completes an episode.
2. The `LibrarianHandoffStep` writes a structured signal file to the Librarian workspace.
3. An IAMQ announcement notifies the Librarian that new content is available.
4. The Librarian picks up the signal file and indexes the episode.

This is the same handoff pattern used by the Journalist agent.

## Peer Agents

| Agent | ID | Typical Interactions |
|-------|----|---------------------|
| Main | `main` | Receives status updates, relays user requests |
| Librarian | `librarian_agent` | Receives episode handoffs and completion announcements |
| Journalist | `journalist_agent` | Provides research content for news-style episodes |
| Mail Agent | `mail_agent` | May forward relevant content for episodes |

## Message Format

All IAMQ messages use JSON. The `body` field is free-form text. For structured data in announcements, use a consistent format:

```
Episode: <title>
Language: <code>
Date: <ISO date>
Files:
  Audio: <path>
  Transcript: <path>
  Show Notes: <path>
  RSS: <feed path>
```

## References

- [IAMQ HTTP API](https://github.com/r3dlex/openclaw-inter-agent-message-queue/blob/main/spec/API.md)
- [IAMQ WebSocket Protocol](https://github.com/r3dlex/openclaw-inter-agent-message-queue/blob/main/spec/PROTOCOL.md)
- [IAMQ Cron Scheduling](https://github.com/r3dlex/openclaw-inter-agent-message-queue/blob/main/spec/CRON.md)
- [Sidecar Client](https://github.com/r3dlex/openclaw-inter-agent-message-queue/tree/main/sidecar)
- [openclaw-main-agent](https://github.com/r3dlex/openclaw-main-agent)
