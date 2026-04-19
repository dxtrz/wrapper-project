import pytest
import json
import uuid
from pathlib import Path
from app import app, safe_username, safe_chat_id, PROFILES_DIR, CHATS_DIR


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def cleanup():
    yield
    for p in PROFILES_DIR.glob('*.json'):
        if p.name not in ['ttrtrt.json']:
            p.unlink(missing_ok=True)
    for c in CHATS_DIR.glob('*.json'):
        c.unlink(missing_ok=True)


class TestUsernameValidation:
    def test_safe_username_valid(self):
        assert safe_username('alice') == 'alice'
        assert safe_username('user_123') == 'user_123'
        assert safe_username('TEST') == 'test'
        assert safe_username('  spaced  ') == 'spaced'

    def test_safe_username_with_spaces_becomes_underscores(self):
        assert safe_username('alice bob') == 'alice_bob'

    def test_safe_username_invalid(self):
        assert safe_username('../evil') is None
        assert safe_username('user@domain') is None
        assert safe_username('') is None
        assert safe_username('a' * 50) is None
        assert safe_username(None) is None
        assert safe_username(123) is None

    def test_safe_username_boundary(self):
        assert safe_username('a') == 'a'
        assert safe_username('a' * 32) == 'a' * 32
        assert safe_username('a' * 33) is None


class TestChatIdValidation:
    def test_safe_chat_id_valid(self):
        valid_uuid = str(uuid.uuid4())
        assert safe_chat_id(valid_uuid) == valid_uuid

    def test_safe_chat_id_invalid(self):
        assert safe_chat_id('not-a-uuid') is None
        assert safe_chat_id('../evil') is None
        assert safe_chat_id('') is None
        assert safe_chat_id(None) is None
        assert safe_chat_id(123) is None


class TestProfileApi:
    def test_get_profile_no_session(self, client):
        res = client.get('/api/profile')
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data['profile'] is None

    def test_post_profile_valid(self, client):
        res = client.post('/api/profile', json={
            'username': 'alice',
            'display_name': 'Alice Wonder',
            'state': 'CA',
            'city': 'Los Angeles',
            'experience': 'connoisseur',
            'use_type': 'recreational',
            'tolerance': 'high',
            'budget': 'premium',
            'preferred_types': ['flower', 'live_rosin'],
            'preferred_effects': ['euphoric', 'relaxed'],
            'flavor_profiles': ['citrus', 'fuel_diesel'],
            'favorite_strains': ['Runtz', 'Gelato 41'],
            'avoid': 'anxiety strains'
        })
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data['success'] is True
        assert data['profile']['username'] == 'alice'
        assert data['profile']['display_name'] == 'Alice Wonder'
        assert data['profile']['state'] == 'CA'
        profile_file = PROFILES_DIR / 'alice.json'
        assert profile_file.exists()
        saved = json.loads(profile_file.read_text())
        assert saved['username'] == 'alice'

    def test_post_profile_missing_username(self, client):
        res = client.post('/api/profile', json={
            'state': 'CA',
            'display_name': 'Bob'
        })
        assert res.status_code == 400
        data = json.loads(res.data)
        assert 'error' in data

    def test_post_profile_invalid_username(self, client):
        res = client.post('/api/profile', json={
            'username': '../evil',
            'state': 'CA'
        })
        assert res.status_code == 400
        data = json.loads(res.data)
        assert 'error' in data
        assert not (PROFILES_DIR / '..').exists() or not (PROFILES_DIR / '..' / 'evil.json').exists()

    def test_post_profile_sanitizes_spaces_in_username(self, client):
        res = client.post('/api/profile', json={
            'username': 'alice bob',
            'state': 'CA'
        })
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data['profile']['username'] == 'alice_bob'

    def test_post_profile_empty_json_body(self, client):
        res = client.post('/api/profile', json={})
        assert res.status_code == 400

    def test_profile_preserves_created_at(self, client):
        res1 = client.post('/api/profile', json={
            'username': 'charlie',
            'state': 'NY',
            'display_name': 'v1'
        })
        data1 = json.loads(res1.data)
        created_at_1 = data1['profile']['created_at']

        res2 = client.post('/api/profile', json={
            'username': 'charlie',
            'state': 'NY',
            'display_name': 'v2'
        })
        data2 = json.loads(res2.data)
        created_at_2 = data2['profile']['created_at']

        assert created_at_1 == created_at_2


class TestRootRoute:
    def test_get_root(self, client):
        res = client.get('/')
        assert res.status_code == 200
        assert b'CannaGuide' in res.data


class TestNewChatRoute:
    def test_new_chat(self, client):
        res = client.post('/api/new-chat')
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data['success'] is True


class TestLogoutRoute:
    def test_logout(self, client):
        client.post('/api/profile', json={
            'username': 'dave',
            'state': 'TX'
        })
        res = client.post('/api/logout')
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data['success'] is True


class TestChatApi:
    def test_chat_no_api_key(self, client, monkeypatch):
        monkeypatch.setenv('GOOGLE_API_KEY', '')
        monkeypatch.setattr('app.GOOGLE_API_KEY', '')

        client.post('/api/profile', json={
            'username': 'eve',
            'state': 'CO'
        })
        res = client.post('/api/chat', json={'message': 'hello'})
        assert res.status_code == 503
        data = json.loads(res.data)
        assert 'error' in data
        assert 'API key' in data['error']

    def test_chat_empty_message(self, client):
        res = client.post('/api/chat', json={'message': ''})
        assert res.status_code == 400
        data = json.loads(res.data)
        assert 'error' in data

    def test_chat_empty_json_body(self, client):
        res = client.post('/api/chat', json={})
        assert res.status_code == 400

    def test_chat_message_required(self, client):
        res = client.post('/api/chat', json={'other_field': 'value'})
        assert res.status_code == 400


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
