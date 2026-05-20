# gws CLI Command Reference
**Discovered:** 2026-05-18

Global flags available on all commands:
- `--format json` — JSON output (default for most; `+read` defaults to text, use `--format json`)
- `--dry-run` — validate/print without executing
- `--page-all` — auto-paginate (NDJSON output, one JSON line per page)
- `--page-limit <N>` — max pages with `--page-all` (default: 10)

Exit codes: 0=success, 1=API error, 2=auth error, 3=validation, 4=discovery, 5=internal

---

## Gmail

### List / Search inbox
```
gws gmail +triage --format json [--max <N>] [--query <QUERY>] [--labels]
```
- Default query: `is:unread`
- Default max: 20
- Returns JSON array of `{id, threadId, subject, from, date, snippet, labels?}`

### Read a message
```
gws gmail +read --id <MESSAGE_ID> --headers --format json
```
- Returns `{id, subject, from, to, date, body}`
- `--html` to get HTML body instead of plain text
- Default format is text; must pass `--format json` explicitly

### Send an email
```
gws gmail +send --to <EMAILS> --subject <SUBJECT> --body <TEXT> --format json [--cc] [--bcc] [--html] [--from]
```
- Returns `{id, threadId, labelIds}` on success

### Save a draft
```
gws gmail +send --to <EMAILS> --subject <SUBJECT> --body <TEXT> --draft --format json
```
- `--draft` saves as draft instead of sending
- Returns draft object with `{id, message: {id, threadId, labelIds}}`

### Reply to a message
```
gws gmail +reply --message-id <MESSAGE_ID> --body <TEXT> --format json [--cc] [--bcc] [--html]
```
- Handles threading (In-Reply-To, References, threadId) automatically
- Returns `{id, threadId, labelIds}`

### List messages (raw API)
```
gws gmail users messages list --params '{"userId":"me","maxResults":<N>,"q":"<QUERY>"}' --format json
```

### Get a message (raw API)
```
gws gmail users messages get --params '{"userId":"me","id":"<ID>","format":"full"}' --format json
```

---

## Calendar

### List upcoming events
```
gws calendar +agenda --format json [--days <N>] [--today] [--tomorrow] [--week] [--calendar <NAME|ID>] [--timezone <TZ>]
```
- Returns JSON array of event objects
- Default: upcoming events from all calendars

### Read a single event
```
gws calendar events get --params '{"calendarId":"primary","eventId":"<ID>"}' --format json
```
- Returns full event object with summary, start, end, attendees, etc.

### Create an event
```
gws calendar +insert --summary <TITLE> --start <ISO8601> --end <ISO8601> --format json [--location] [--description] [--attendee <EMAIL> ...] [--meet] [--calendar <ID>]
```
- RFC3339 times, e.g. `2026-06-17T09:00:00-07:00`
- Returns `{id, htmlLink, summary, start, end}`

### Update an event (patch)
```
gws calendar events patch --params '{"calendarId":"primary","eventId":"<ID>"}' --json '<PARTIAL_EVENT_JSON>' --format json
```
- Only include fields to change in `--json`
- Returns updated event object

### Delete an event
```
gws calendar events delete --params '{"calendarId":"primary","eventId":"<ID>"}' --format json
```
- Returns empty body on success (exit 0)

---

## Drive

### List files
```
gws drive files list --params '{"pageSize":<N>,"q":"<QUERY>","fields":"files(id,name,mimeType,modifiedTime,size,parents)"}' --format json
```
- To filter by folder: `"'<FOLDER_ID>' in parents"`
- Returns `{files: [{id, name, mimeType, modifiedTime, size, parents}]}`

### Get file metadata
```
gws drive files get --params '{"fileId":"<ID>","fields":"id,name,mimeType,modifiedTime,size,parents,webViewLink"}' --format json
```
- Returns single file metadata object

### Upload a file
```
gws drive +upload <LOCAL_PATH> --format json [--parent <FOLDER_ID>] [--name <TARGET_NAME>]
```
- MIME type auto-detected from extension
- Returns `{id, name, mimeType, size, parents, webViewLink}`
