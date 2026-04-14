from flask import Flask, render_template, request, jsonify, session
import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'canna-dev-secret-change-me')

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')

DATA_DIR = Path('data')
PROFILES_DIR = DATA_DIR / 'profiles'
CHATS_DIR = DATA_DIR / 'chats'

for d in [PROFILES_DIR, CHATS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


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
        username = session.get('username')
        if not username:
            return jsonify({'profile': None})
        data = load_json(PROFILES_DIR / f'{username}.json')
        return jsonify({'profile': data})

    body = request.get_json()
    username = body.get('username', '').strip().lower().replace(' ', '_')
    if not username:
        return jsonify({'error': 'Username is required'}), 400

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

    body = request.get_json()
    user_message = body.get('message', '').strip()
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400

    username = session.get('username')
    chat_id = session.setdefault('chat_id', str(uuid.uuid4()))

    profile = load_json(PROFILES_DIR / f'{username}.json') if username else None
    history = load_json(CHATS_DIR / f'{chat_id}.json') or []

    from system_prompt import build_system_prompt
    sys_prompt = build_system_prompt(profile)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GOOGLE_API_KEY)

        contents = []
        for msg in history:
            contents.append(types.Content(
                role=msg['role'],
                parts=[types.Part(text=msg['content'])]
            ))
        contents.append(types.Content(
            role='user',
            parts=[types.Part(text=user_message)]
        ))

        response = client.models.generate_content(
            model='gemini-2.0-flash',
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

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/new-chat', methods=['POST'])
def new_chat():
    session['chat_id'] = str(uuid.uuid4())
    return jsonify({'success': True})


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
