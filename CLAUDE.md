# CannaGuide

Flask + Gemini 1.5 Flash wrapper. A cannabis sourcing assistant with a 4-step profile wizard, a chat UI, and a persona defined in [system_prompt.py](system_prompt.py). Google Search tool is enabled on the Gemini call so the model can pull live dispensary info.

## Run

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in GOOGLE_API_KEY + SECRET_KEY
python app.py          # http://localhost:8080
```

`FLASK_DEBUG=1` enables debug mode. Unset in anything that isn't local dev.

## Layout

- [app.py](app.py) — Flask app. Five routes: `/`, `/api/profile` (GET/POST), `/api/chat` (POST), `/api/new-chat` (POST), `/api/logout` (POST).
- [system_prompt.py](system_prompt.py) — `build_system_prompt(profile)` returns the full CannaGuide persona with the user profile block appended.
- [templates/index.html](templates/index.html) — wizard overlay + main app shell.
- [static/app.js](static/app.js) — wizard state machine, chat send/receive, profile sidebar.
- [static/style.css](static/style.css) — styles.
- `data/profiles/<username>.json` — per-user profile (created by wizard).
- `data/chats/<chat_id>.json` — per-session chat history. `chat_id` is a UUID stored in the Flask session cookie.

## Conventions

- **Persistence is JSON files on disk**, not a database. Keep it that way until chat volume forces a move — that's the point of this wrapper.
- **Secrets via `.env` only.** Never commit keys. `.env` is gitignored; `.env.example` is the template.
- **Usernames must match `^[a-z0-9_]{1,32}$`** before being used as a filename — anywhere you read/write `data/profiles/*`, validate first.
- **LLM output is untrusted HTML.** The frontend renders model replies as markdown via `marked`; sanitize with DOMPurify before `innerHTML`. Never bypass.
- **Chat history is windowed** to the last N turns when sent to Gemini (see `CHAT_HISTORY_WINDOW` in [app.py](app.py)). Full history is still persisted to disk.
- **Errors**: log server-side, return a generic message to the client. Don't `jsonify({'error': str(e)})` — that leaks stack details.
- **System prompt edits** (strain lists, state market knowledge, response style) happen in [system_prompt.py](system_prompt.py). The user profile block is appended at the bottom — keep the `base + user_section` shape.
- **Frontend is vanilla JS + Jinja.** No build step, no framework. Resist adding one.

## When adding a feature

1. If it needs a new API route → add to [app.py](app.py), follow the existing JSON-in/JSON-out shape, validate inputs at the boundary.
2. If it needs new persona behavior → edit the `base` string in [system_prompt.py](system_prompt.py). Keep sections in the existing markdown hierarchy.
3. If it needs new profile fields → update the wizard in [templates/index.html](templates/index.html) + [static/app.js](static/app.js) (`wizardData`, `collectStep`, `editProfile`), the profile dict in [app.py:57](app.py:57), and the personalization block in [system_prompt.py](system_prompt.py).
4. If it touches chat UI → remember model output passes through `marked.parse` → sanitize.

## Not present yet

- No tests. No linter config. No CI.
- No auth — session cookie + username is the whole identity system.
- No rate limiting on `/api/chat` — each call hits Gemini with `google_search` enabled, so it's not free.
