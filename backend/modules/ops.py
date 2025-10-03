from flask import Blueprint, jsonify
from datetime import datetime, timedelta
import io, json, random, base64, zipfile

from .ledger import LEDGER, compute_event_hash
from .threats import THREATS
from .incidents import INCIDENTS
from .commands import DRONE_STATE, COMMAND_LOG

ops_bp = Blueprint('ops', __name__)


@ops_bp.route('/ops/mode', methods=['GET'])
def ops_mode():
    """Return an adaptive operations / energy mode state.
    HIGH_ALERT: any high confidence threat >=0.85 in last 5m
    ECO: no threats in last 10m
    NORMAL: otherwise
    """
    now = datetime.utcnow()
    recent = [t for t in THREATS.values() if (now - datetime.fromisoformat(t['created_at'].rstrip('Z')))< timedelta(minutes=10)]
    high = any(t['confidence'] >= 0.85 and (now - datetime.fromisoformat(t['created_at'].rstrip('Z'))) < timedelta(minutes=5) for t in THREATS.values())
    if high:
        mode = 'HIGH_ALERT'
    elif not recent:
        mode = 'ECO'
    else:
        mode = 'NORMAL'
    # simulated savings: eco saves 40%, normal 15%, high alert -10% (surge)
    savings = 0.4 if mode=='ECO' else 0.15 if mode=='NORMAL' else -0.10
    return jsonify({'mode': mode, 'simulated_energy_delta': savings, 'threats_recent_10m': len(recent)})


@ops_bp.route('/ros/summary', methods=['GET'])
def ros_summary():
    """Return a simulated Return on Security (ROS) summary based on current threats & incidents."""
    threat_count = len(THREATS)
    incidents_open = len([i for i in INCIDENTS.values() if i['status']=='open'])
    # simplistic model: avoided_cost = base * (threat_count + incidents_open*2)
    base_unit = 12500  # arbitrary unit cost per significant event
    avoided = base_unit * (threat_count + incidents_open*2)
    est_breach_cost = 550000  # sample potential loss figure
    ros_ratio = (avoided)/(est_breach_cost or 1)
    return jsonify({
        'threat_count': threat_count,
        'incidents_open': incidents_open,
        'avoided_cost_estimate': avoided,
        'single_breach_reference': est_breach_cost,
        'ros_ratio': ros_ratio
    })

@ops_bp.route('/risk/score', methods=['GET'])
def risk_score():
    # Combine: number of unauthorized threats, max confidence, open incidents
    unauthorized = [t for t in THREATS.values() if not t.get('authorized')]
    max_conf = max([t['confidence'] for t in THREATS.values()], default=0)
    open_inc = len([i for i in INCIDENTS.values() if i['status']=='open'])
    # heuristic scoring
    score = 0
    score += min(60, len(unauthorized) * 12)
    score += int(max_conf * 25)
    score += min(15, open_inc * 5)
    score = min(100, score)
    return jsonify({
        'score': score,
        'components': {
            'unauthorized_count': len(unauthorized),
            'max_confidence': max_conf,
            'open_incidents': open_inc
        }
    })


@ops_bp.route('/evidence/bundle', methods=['GET'])
def evidence_bundle():
    """Produce a downloadable evidence bundle (zip -> base64) for demo purposes."""
    bundle = {
        'generated_at': datetime.utcnow().isoformat()+'Z',
        'ledger_tail': LEDGER[-50:],
        'threats_snapshot': list(THREATS.values())[-25:],
        'incidents': list(INCIDENTS.values()),
        'drone_state': DRONE_STATE,
        'command_log_tail': COMMAND_LOG[-25:],
    }
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('evidence.json', json.dumps(bundle, indent=2))
    b64 = base64.b64encode(mem.getvalue()).decode()
    return jsonify({'filename': 'project_kavach_evidence_bundle.zip', 'base64': b64, 'size_bytes': len(mem.getvalue())})


@ops_bp.route('/ledger/corrupt', methods=['POST'])
def corrupt_ledger():
    """Intentionally corrupt one random ledger entry's chain_hash for demo verification failure."""
    if len(LEDGER) < 3:
        return jsonify({'error': 'not_enough_events'}), 400
    target = random.choice(LEDGER[1:-1])  # avoid first & last for easier demo
    original = target['chain_hash']
    # flip a couple of characters deterministically
    mutated = list(original)
    mutated[5] = '0' if mutated[5] != '0' else 'f'
    mutated[17] = 'a' if mutated[17] != 'a' else '1'
    target['chain_hash'] = ''.join(mutated)
    return jsonify({'corrupted_entry_id': target['id'], 'new_chain_hash': target['chain_hash']})
