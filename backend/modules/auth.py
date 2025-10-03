from flask import Blueprint, request, jsonify
import time, jwt, os

auth_bp = Blueprint('auth', __name__)
JWT_SECRET = os.environ.get('JWT_SECRET', 'dev_secret_change_me')
JWT_ISSUER = 'tejas-platform'

# Dummy user store for MVP
dummy_users = {
    'operator': {'password': 'op123', 'roles': ['operator']},
    'supervisor': {'password': 'sup123', 'roles': ['operator','supervisor']},
    'auditor': {'password': 'aud123', 'roles': ['auditor']},
    'mladmin': {'password': 'ml123', 'roles': ['ml_admin']},
}

def issue_token(username, roles):
    now = int(time.time())
    payload = {
        'sub': username,
        'roles': roles,
        'iat': now,
        'exp': now + 3600,
        'iss': JWT_ISSUER
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json or {}
    u = data.get('username'); p = data.get('password')
    user = dummy_users.get(u)
    if not user or user['password'] != p:
        return jsonify({'error': 'invalid_credentials'}), 401
    token = issue_token(u, user['roles'])
    return jsonify({'access_token': token, 'token_type': 'bearer', 'expires_in': 3600})
