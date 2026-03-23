---
id: ARCH-004
title: Inter-Agent Collaboration
domain: architecture
rules: false
---

# ARCH-004: Inter-Agent Collaboration

## Context

The Podcaster agent operates within the OpenClaw multi-agent system alongside the Librarian, Journalist, Main, and other agents. It needs to:

- Announce episode completions for archival (Librarian).
- Request research content for news episodes (Journalist).
- Receive production requests from other agents.
- Stay visible and responsive to the orchestrator (Main).

The Journalist agent already established two collaboration patterns: IAMQ for messaging and file-based handoff for the Librarian.

## Decision

Use both IAMQ and file-based Librarian handoff, matching the Journalist agent's established pattern:

**IAMQ (Inter-Agent Message Queue):**
- Register as `podcast_agent`.
- Send heartbeats every 2 minutes via the scheduler.
- Check inbox on each heartbeat for pending requests.
- Announce pipeline completions to `librarian_agent`.
- Request content from `journalist_agent` when needed.
- Use `replyTo` threading for request/response conversations.

**File-based Librarian Handoff:**
- Write structured signal files to `$LIBRARIAN_AGENT_WORKSPACE`.
- Include episode metadata (title, language, file paths, timestamps).
- The Librarian picks up and indexes these signals independently.
- Same directory mount pattern as the Journalist agent.

## Consequences

**Positive:**
- Consistent inter-agent protocol across all OpenClaw agents.
- Two channels (IAMQ + file handoff) provide redundancy.
- Heartbeats keep the agent discoverable without polling.
- Decoupled from Librarian availability — file handoff is async.

**Negative:**
- Depends on IAMQ service being available (non-fatal if down).
- File-based handoff requires shared volume mounts in Docker.
- Two communication channels to maintain and keep in sync.

## Compliance and Enforcement

- The scheduler handles IAMQ registration and heartbeats automatically.
- Every pre-built pipeline includes `IAMQAnnounceStep` and `LibrarianHandoffStep`.
- IAMQ connection failures are logged but do not block pipeline execution.
- The `AGENTS.md` file documents all peer agents and their IDs.
