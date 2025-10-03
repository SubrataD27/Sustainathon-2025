# API Specification (MVP)

## Auth

POST /api/auth/login

* body: `{ "username": "operator", "password": "op123" }`
* 200: `{ access_token, token_type, expires_in }`

## Threats

* GET /api/threats/ – list threats
* POST /api/threats/ – create simulated threat
* GET /api/threats/{id} – retrieve threat

## Commands

* POST /api/commands/dispatch – `{ threat_id, coordinates }`
* POST /api/commands/return
* POST /api/commands/abort
* GET /api/commands/log

## Incidents

* GET /api/incidents/
* POST /api/incidents/ – `{ threat_id, action_taken }`
* GET /api/incidents/{id}
* POST /api/incidents/{id}/close

## Ledger

* POST /api/ledger/append – `{ event_type, payload }`
* GET /api/ledger/latest
* GET /api/ledger/verify
* GET /api/ledger/all

## WebSocket (Planned)

`ws://HOST:PORT/ws/stream` – multiplex events (threats, ledger, commands)

## Roles (Future Enforcement)

* operator: list/read threats, issue dispatch/return/abort
* supervisor: all operator + close incidents
* auditor: read-only + ledger verify
* ml_admin: deploy model endpoints

## Error Format

`{ "error": "code", "detail": "(optional)" }`

## Pagination (Future)

* Query params: `?limit=` & `cursor=`

## Rate Limiting (Future)

* 429 with `Retry-After` header

