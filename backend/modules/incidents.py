from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid

incidents_bp = Blueprint('incidents', __name__)

INCIDENTS = {}

@incidents_bp.route('/', methods=['GET'])
def list_incidents():
    return jsonify(list(INCIDENTS.values()))

@incidents_bp.route('/<iid>', methods=['GET'])
def get_incident(iid):
    inc = INCIDENTS.get(iid)
    if not inc:
        return jsonify({'error':'not_found'}), 404
    return jsonify(inc)

@incidents_bp.route('/', methods=['POST'])
def create_incident():
    data = request.json or {}
    iid = str(uuid.uuid4())
    inc = {
        'id': iid,
        'threat_id': data.get('threat_id'),
        'action_taken': data.get('action_taken','auto_dispatch'),
        'status': 'open',
        'created_at': datetime.utcnow().isoformat()+'Z'
    }
    INCIDENTS[iid] = inc
    return jsonify(inc), 201

@incidents_bp.route('/<iid>/close', methods=['POST'])
def close_incident(iid):
    inc = INCIDENTS.get(iid)
    if not inc:
        return jsonify({'error':'not_found'}), 404
    inc['status'] = 'closed'
    inc['closed_at'] = datetime.utcnow().isoformat()+'Z'
    return jsonify(inc)
