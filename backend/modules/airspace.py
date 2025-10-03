from flask import Blueprint, jsonify, request
import uuid

airspace_bp = Blueprint('airspace', __name__)

WHITELIST = set()  # remote IDs allowed

@airspace_bp.route('/airspace/whitelist', methods=['GET'])
def get_whitelist():
    return jsonify(sorted(list(WHITELIST)))

@airspace_bp.route('/airspace/whitelist', methods=['POST'])
def add_whitelist():
    data = request.json or {}
    rid = data.get('remote_id') or f'RID-{str(uuid.uuid4())[:8]}'
    WHITELIST.add(rid)
    return jsonify({'added': rid, 'total': len(WHITELIST)}), 201

@airspace_bp.route('/airspace/whitelist/<rid>', methods=['DELETE'])
def remove_whitelist(rid):
    if rid in WHITELIST:
        WHITELIST.remove(rid)
        return jsonify({'removed': rid, 'total': len(WHITELIST)})
    return jsonify({'error':'not_found'}), 404
