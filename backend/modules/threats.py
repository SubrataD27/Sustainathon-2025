from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid
import random
from .airspace import WHITELIST

threats_bp = Blueprint('threats', __name__)

# In-memory store for rapid MVP iteration
THREATS = {}

@threats_bp.route('/', methods=['GET'])
def list_threats():
    return jsonify(list(THREATS.values()))

@threats_bp.route('/<threat_id>', methods=['GET'])
def get_threat(threat_id):
    t = THREATS.get(threat_id)
    if not t:
        return jsonify({'error': 'not_found'}), 404
    return jsonify(t)

@threats_bp.route('/', methods=['POST'])
def create_threat():
    data = request.json or {}
    tid = str(uuid.uuid4())
    remote_id = data.get('remote_id') or f'RID-{str(uuid.uuid4())[:6]}'
    threat = {
        'id': tid,
        'class': data.get('class', 'unknown'),
        'confidence': data.get('confidence', 0.5),
        'location': data.get('location', {'lat':0,'lon':0}),
        'status': 'detected',
        'created_at': datetime.utcnow().isoformat()+'Z',
        'remote_id': remote_id,
        'authorized': remote_id in WHITELIST
    }
    THREATS[tid] = threat
    return jsonify(threat), 201

@threats_bp.route('/seed', methods=['POST'])
def seed():
    classes = ['consumer_quadcopter','prosumer_quadcopter','bird','jammer_sweep']
    generated = []
    base_lat, base_lon = 28.50, 77.60
    for _ in range(int((request.json or {}).get('count', 6))):
        tid = str(uuid.uuid4())
        cls = random.choice(classes)
        remote_id = f'RID-{str(uuid.uuid4())[:6]}'
        threat = {
            'id': tid,
            'class': cls,
            'confidence': round(random.uniform(0.55, 0.97),2),
            'location': {'lat': base_lat + random.uniform(-0.01,0.01), 'lon': base_lon + random.uniform(-0.01,0.01)},
            'status': 'detected',
            'created_at': datetime.utcnow().isoformat()+'Z',
            'remote_id': remote_id,
            'authorized': remote_id in WHITELIST
        }
        THREATS[tid] = threat
        generated.append(threat)
    return jsonify({'generated': generated, 'total': len(THREATS)}), 201
