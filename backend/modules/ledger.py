from flask import Blueprint, request, jsonify
from datetime import datetime
import hashlib, json, uuid

ledger_bp = Blueprint('ledger', __name__)

LEDGER = []  # in-memory linear chain for MVP

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',',':'))

def compute_event_hash(payload):
    return hashlib.sha256(canonical(payload).encode()).hexdigest()

def append_event(event_type, payload):
    prev_chain_hash = LEDGER[-1]['chain_hash'] if LEDGER else '0'*64
    event_hash = compute_event_hash(payload)
    chain_input = f"{prev_chain_hash}|{event_hash}|{payload.get('timestamp')}|0"
    chain_hash = hashlib.sha256(chain_input.encode()).hexdigest()
    entry = {
        'id': len(LEDGER)+1,
        'event_type': event_type,
        'payload': payload,
        'event_hash': event_hash,
        'prev_chain_hash': prev_chain_hash,
        'chain_hash': chain_hash
    }
    LEDGER.append(entry)
    return entry

@ledger_bp.route('/append', methods=['POST'])
def api_append():
    data = request.json or {}
    event_type = data.get('event_type')
    payload = data.get('payload', {})
    if 'timestamp' not in payload:
        payload['timestamp'] = datetime.utcnow().isoformat()+'Z'
    entry = append_event(event_type, payload)
    return jsonify(entry), 201

@ledger_bp.route('/latest', methods=['GET'])
def latest():
    return jsonify(LEDGER[-1] if LEDGER else {})

@ledger_bp.route('/verify', methods=['GET'])
def verify():
    failures = []
    last = '0'*64
    for e in LEDGER:
        recomputed_event_hash = compute_event_hash(e['payload'])
        chain_input = f"{last}|{recomputed_event_hash}|{e['payload'].get('timestamp')}|0"
        expected_chain = hashlib.sha256(chain_input.encode()).hexdigest()
        if expected_chain != e['chain_hash'] or recomputed_event_hash != e['event_hash']:
            failures.append(e['id'])
            break
        last = e['chain_hash']
    return jsonify({'valid': len(failures)==0, 'failures': failures, 'length': len(LEDGER)})

@ledger_bp.route('/summary', methods=['GET'])
def summary():
    window = int(request.args.get('window', 25))
    recent = LEDGER[-window:]
    # quick verify subset only
    last = '0'*64 if len(LEDGER)==len(recent) else LEDGER[-(window+1)]['chain_hash'] if len(LEDGER)>window else '0'*64
    subset_valid = True
    for e in recent:
        recomputed_event_hash = compute_event_hash(e['payload'])
        chain_input = f"{last}|{recomputed_event_hash}|{e['payload'].get('timestamp')}|0"
        expected_chain = hashlib.sha256(chain_input.encode()).hexdigest()
        if expected_chain != e['chain_hash'] or recomputed_event_hash != e['event_hash']:
            subset_valid = False
            break
        last = e['chain_hash']
    # also quick full-chain status (without listing failures) for UI badge
    last = '0'*64
    full_valid = True
    for e in LEDGER:
        recomputed_event_hash = compute_event_hash(e['payload'])
        chain_input = f"{last}|{recomputed_event_hash}|{e['payload'].get('timestamp')}|0"
        expected_chain = hashlib.sha256(chain_input.encode()).hexdigest()
        if expected_chain != e['chain_hash'] or recomputed_event_hash != e['event_hash']:
            full_valid = False
            break
        last = e['chain_hash']
    return jsonify({
        'length': len(LEDGER),
        'window': window,
        'recent_valid': subset_valid,
        'full_valid': full_valid,
        'latest_chain_hash': LEDGER[-1]['chain_hash'] if LEDGER else None,
        'recent': [ {'id': e['id'], 'event_type': e['event_type'], 'chain_hash': e['chain_hash']} for e in recent ]
    })

@ledger_bp.route('/all', methods=['GET'])
def all_entries():
    return jsonify(LEDGER)
