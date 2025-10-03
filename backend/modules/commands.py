from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid

from .ledger import append_event
from .incidents import INCIDENTS  # for auto incident creation

commands_bp = Blueprint('commands', __name__)

COMMAND_LOG = []

DRONE_STATE = {
    'id': 'demo-drone-1',
    'status': 'idle',
    'location': {'lat': 28.5000, 'lon': 77.6000},
    'last_command_at': None,
    'current_threat_id': None,
    'origin_location': {'lat': 28.5000, 'lon': 77.6000},
    'target_location': None,
    'route_started_at': None,
    'base_location': {'lat': 28.5000, 'lon': 77.6000}
}

def _append_command(command, extra=None):
    entry = {
        'id': str(uuid.uuid4()),
        'command': command,
        'timestamp': datetime.utcnow().isoformat()+'Z',
        'extra': extra or {},
        'result': 'accepted'
    }
    COMMAND_LOG.append(entry)
    ledger_payload = {'timestamp': entry['timestamp'], 'command': command, 'command_id': entry['id'], **(extra or {})}
    append_event('command_'+command, ledger_payload)
    return entry

def _update_drone_position():
    """Simulate drone movement linearly over a fixed travel time between origin and target."""
    if DRONE_STATE.get('route_started_at') and DRONE_STATE.get('target_location'):
        try:
            start_ts = datetime.fromisoformat(DRONE_STATE['route_started_at'].rstrip('Z'))
        except Exception:
            return
        travel_time = 60  # seconds to reach target
        elapsed = (datetime.utcnow() - start_ts).total_seconds()
        frac = min(1.0, max(0.0, elapsed / travel_time))
        o = DRONE_STATE['origin_location'] or DRONE_STATE['location']
        t = DRONE_STATE['target_location']
        DRONE_STATE['location'] = {
            'lat': o['lat'] + (t['lat'] - o['lat']) * frac,
            'lon': o['lon'] + (t['lon'] - o['lon']) * frac
        }
        if frac >= 1.0 and DRONE_STATE['status'] == 'en_route':
            DRONE_STATE['status'] = 'on_station'

@commands_bp.route('/dispatch', methods=['POST'])
def dispatch():
    data = request.json or {}
    threat_id = data.get('threat_id')
    coords = data.get('coordinates') or DRONE_STATE['location']
    DRONE_STATE['origin_location'] = DRONE_STATE['location']
    DRONE_STATE['target_location'] = coords
    DRONE_STATE['route_started_at'] = datetime.utcnow().isoformat()+'Z'
    DRONE_STATE['status'] = 'en_route'
    DRONE_STATE['current_threat_id'] = threat_id
    DRONE_STATE['last_command_at'] = datetime.utcnow().isoformat()+'Z'
    entry = _append_command('dispatch_drone', {'threat_id': threat_id, 'coordinates': coords})
    # Auto incident creation
    inc_id = str(uuid.uuid4())
    incident = {
        'id': inc_id,
        'threat_id': threat_id,
        'action_taken': 'auto_dispatch',
        'status': 'open',
        'created_at': entry['timestamp']
    }
    INCIDENTS[inc_id] = incident
    append_event('incident_opened', {'timestamp': entry['timestamp'], 'incident_id': inc_id, 'threat_id': threat_id})
    return jsonify(entry), 202

@commands_bp.route('/return', methods=['POST'])
def return_to_base():
    DRONE_STATE['origin_location'] = DRONE_STATE['location']
    DRONE_STATE['target_location'] = DRONE_STATE['base_location']
    DRONE_STATE['route_started_at'] = datetime.utcnow().isoformat()+'Z'
    DRONE_STATE['status'] = 'returning'
    DRONE_STATE['current_threat_id'] = None
    DRONE_STATE['last_command_at'] = datetime.utcnow().isoformat()+'Z'
    entry = _append_command('return_to_base')
    return jsonify(entry), 202

@commands_bp.route('/abort', methods=['POST'])
def abort():
    DRONE_STATE['status'] = 'idle'
    DRONE_STATE['current_threat_id'] = None
    DRONE_STATE['last_command_at'] = datetime.utcnow().isoformat()+'Z'
    entry = _append_command('abort_interception')
    return jsonify(entry), 202

@commands_bp.route('/log', methods=['GET'])
def command_log():
    return jsonify(COMMAND_LOG[-200:])

@commands_bp.route('/drone', methods=['GET'])
def drone():
    _update_drone_position()
    return jsonify(DRONE_STATE)
