from flask import Flask, jsonify, request
from flask_cors import CORS
import time

from modules.auth import auth_bp
from modules.threats import threats_bp
from modules.commands import commands_bp
from modules.ledger import ledger_bp
from modules.incidents import incidents_bp
from modules.ws import ws_bp
from modules.ops import ops_bp
from modules.airspace import airspace_bp
from modules.commands import COMMAND_LOG, DRONE_STATE
from modules.threats import THREATS
from modules.ledger import LEDGER

app = Flask(__name__)
CORS(app)

# Blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(threats_bp, url_prefix='/api/threats')
app.register_blueprint(commands_bp, url_prefix='/api/commands')
app.register_blueprint(ledger_bp, url_prefix='/api/ledger')
app.register_blueprint(incidents_bp, url_prefix='/api/incidents')
app.register_blueprint(ws_bp, url_prefix='/api')
app.register_blueprint(ops_bp, url_prefix='/api')
app.register_blueprint(airspace_bp, url_prefix='/api')

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'time': time.time()
    })

@app.route('/api/dashboard/summary')
def dashboard_summary():
    # Compute basic distributions
    classes = {}
    for t in THREATS.values():
        classes[t['class']] = classes.get(t['class'], 0) + 1
    return jsonify({
        'threat_count': len(THREATS),
        'drone_state': DRONE_STATE,
        'command_count': len(COMMAND_LOG),
        'latest_command': COMMAND_LOG[-1] if COMMAND_LOG else None,
        'ledger_length': len(LEDGER),
        'class_distribution': classes,
        'timestamp': time.time()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
