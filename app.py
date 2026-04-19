from flask import Flask, render_template, request, jsonify, session
import os
import re
import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
log = logging.getLogger('cannaguide')

FLASK_DEBUG = os.environ.get('FLASK_DEBUG', '').lower() in ('1', 'true', 'yes')

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if FLASK_DEBUG:
        SECRET_KEY = 'canna-dev-secret-change-me'
        log.warning('SECRET_KEY not set — using dev fallback (debug mode only).')
    else:
        raise RuntimeError('SECRET_KEY must be set in .env for non-debug runs.')

app = Flask(__name__)
app.secret_key = SECRET_KEY

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')

DATA_DIR = Path('data')
PROFILES_DIR = DATA_DIR / 'profiles'
CHATS_DIR = DATA_DIR / 'chats'

for d in [PROFILES_DIR, CHATS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

USERNAME_RE = re.compile(r'^[a-z0-9_]{1,32}$')
CHAT_ID_RE = re.compile(r'^[a-f0-9-]{36}$')
CHAT_HISTORY_WINDOW = 20


def safe_username(raw):
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip().lower().replace(' ', '_')
    return cleaned if USERNAME_RE.match(cleaned) else None


def safe_chat_id(raw):
    return raw if isinstance(raw, str) and CHAT_ID_RE.match(raw) else None


def load_json(path):
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text())
    return None


def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/profile', methods=['GET', 'POST'])
def profile_api():
    if request.method == 'GET':
        username = safe_username(session.get('username'))
        if not username:
            return jsonify({'profile': None})
        data = load_json(PROFILES_DIR / f'{username}.json')
        return jsonify({'profile': data})

    body = request.get_json() or {}
    username = safe_username(body.get('username', ''))
    if not username:
        return jsonify({'error': 'Username must be 1–32 chars, letters/numbers/underscore only.'}), 400

    existing = load_json(PROFILES_DIR / f'{username}.json')
    created_at = existing['created_at'] if existing else datetime.now().isoformat()

    profile = {
        'username': username,
        'display_name': body.get('display_name', username).strip() or username,
        'state': body.get('state', ''),
        'city': body.get('city', '').strip(),
        'experience': body.get('experience', 'enthusiast'),
        'use_type': body.get('use_type', 'recreational'),
        'tolerance': body.get('tolerance', 'medium'),
        'budget': body.get('budget', 'mid'),
        'preferred_types': body.get('preferred_types', []),
        'preferred_effects': body.get('preferred_effects', []),
        'flavor_profiles': body.get('flavor_profiles', []),
        'favorite_strains': body.get('favorite_strains', []),
        'avoid': body.get('avoid', '').strip(),
        'created_at': created_at,
        'updated_at': datetime.now().isoformat(),
    }

    save_json(PROFILES_DIR / f'{username}.json', profile)
    session['username'] = username
    session.setdefault('chat_id', str(uuid.uuid4()))

    return jsonify({'success': True, 'profile': profile})


@app.route('/api/chat', methods=['POST'])
def chat_api():
    if not GOOGLE_API_KEY:
        return jsonify({
            'error': 'No API key set. Add your GOOGLE_API_KEY to the .env file and restart.'
        }), 503

    body = request.get_json() or {}
    user_message = body.get('message', '').strip()
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400

    username = safe_username(session.get('username'))

    chat_id = safe_chat_id(session.get('chat_id'))
    if not chat_id:
        chat_id = str(uuid.uuid4())
        session['chat_id'] = chat_id

    profile = load_json(PROFILES_DIR / f'{username}.json') if username else None
    history = load_json(CHATS_DIR / f'{chat_id}.json') or []

    from system_prompt import build_system_prompt
    sys_prompt = build_system_prompt(profile)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GOOGLE_API_KEY)

        windowed = history[-CHAT_HISTORY_WINDOW * 2:]
        contents = []
        for msg in windowed:
            contents.append(types.Content(
                role=msg['role'],
                parts=[types.Part(text=msg['content'])]
            ))
        contents.append(types.Content(
            role='user',
            parts=[types.Part(text=user_message)]
        ))

        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=sys_prompt,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.7,
                max_output_tokens=2048,
            )
        )

        reply = response.text

        history.append({
            'role': 'user',
            'content': user_message,
            'ts': datetime.now().isoformat()
        })
        history.append({
            'role': 'model',
            'content': reply,
            'ts': datetime.now().isoformat()
        })
        save_json(CHATS_DIR / f'{chat_id}.json', history)

        return jsonify({'response': reply})

    except Exception:
        log.exception('chat_api failed (chat_id=%s user=%s)', chat_id, username)
        return jsonify({'error': 'The model call failed. Check server logs and try again.'}), 500


@app.route('/api/new-chat', methods=['POST'])
def new_chat():
    session['chat_id'] = str(uuid.uuid4())
    return jsonify({'success': True})


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})


if __name__ == '__main__':
    app.run(debug=FLASK_DEBUG, port=int(os.environ.get('PORT', 8080)))
