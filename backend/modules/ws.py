from flask import Blueprint, jsonify

ws_bp = Blueprint('ws', __name__)

# Placeholder: In production use a separate ASGI server for true WebSocket streaming.
@ws_bp.route('/stream/info')
def stream_info():
    return jsonify({'message':'Upgrade to WebSocket server placeholder', 'ws_url':'wss://localhost:8001/stream'})
