---
name: ableton-mcp
description: Manages the TCP socket communication and control protocol for Ableton Live via the ahujasid/ableton-mcp server. Use this when the user requests to connect to Live, send MIDI data, or control track parameters.
---

# Ableton MCP Interaction Skill

## Goal
Establish and maintain a stable, secure bridge between the Python backend and Ableton Live using the Model Context Protocol (MCP) over a local TCP connection.

## Technical Specifications
- **Host:** 127.0.0.1 (Strict Localhost)
- **Port:** 9877
- **Protocol:** TCP/IP using JSON-encoded payloads.
- **Remote Script Path:** D:\Sync\00 PC Sharing\Ableton\User Library\Remote Scripts

## Implementation Logic
When this skill is activated, the agent must follow these steps for any communication attempt:

1. **Safety Check:** Ensure the destination IP is strictly `127.0.0.1`. Never attempt to bind to `0.0.0.0` or any external interface.
2. **Payload Structure:** All messages must be formatted as JSON.
   - Example Ping: `{"jsonrpc": "2.0", "method": "ping", "params": {}, "id": 1}`
3. **Connection Handling:**
   - Use a non-blocking socket approach or a short timeout (2.0 seconds) to prevent the application from hanging if Ableton is not open.
   - Gracefully handle `ConnectionRefusedError` by instructing the user to verify that Ableton Live is running with the Remote Script enabled.

## Examples of Usage
- **User Query:** "Is Ableton connected?"
- **Agent Action:** Utilize the `test_ableton_connection` tool in `backend/gemini_client.py` to send a ping to port 9877.
- **User Query:** "Send a C3 note to track 1."
- **Agent Action:** Construct an MCP tool call targeting the `ableton-mcp` server with the relevant MIDI parameters.

## Constraints
- Do not attempt to use MIDI ports directly; always route through the TCP bridge on port 9877.
- If the port is occupied by another process (e.g., Armoury Crate or other audio utilities), notify the user immediately and suggest a port scan.
- Ensure all background listener threads are marked as `daemon=True` so they do not prevent the IDE or the backend from closing.
- Always use `self.log_message()` instead of `print()` for debugging, as Ableton redirects stdout to its internal Log.txt.