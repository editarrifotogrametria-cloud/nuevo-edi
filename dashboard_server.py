#!/usr/bin/env python3
"""
GNSS.AI Dashboard Server v3.0 - ML Enhanced
Servidor web con WebSocket para dashboard en tiempo real
"""

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import json
import time
import threading
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gnssai-ml-2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

current_stats = {
    'position': {'lat': 0, 'lon': 0, 'alt': 0},
    'satellites': 0,
    'quality': 0,
    'hdop': 0,
    'nmea_sent': 0,
    'rtcm_sent': 0,
    'ml_corrections': 0,
    'format_switches': 0,
    'los_sats': 0,
    'multipath_sats': 0,
    'nlos_sats': 0,
    'avg_confidence': 0,
    'estimated_accuracy': 0,
    'rtk_status': 'NO_FIX',
    'format': 'NMEA',
    'uptime': 0,
    'last_update': datetime.now().isoformat()
}

JSON_FILE = '/tmp/gnssai_dashboard_data.json'
start_time = time.time()

def read_json_data():
    """Lee JSON cada 500ms y emite vía WebSocket"""
    last_mtime = 0
    print("📊 Lector de datos iniciado...")
    
    while True:
        try:
            if os.path.exists(JSON_FILE):
                stat = os.stat(JSON_FILE)
                
                if stat.st_mtime > last_mtime:
                    with open(JSON_FILE, 'r') as f:
                        data = json.load(f)
                        current_stats.update(data)
                        current_stats['last_update'] = datetime.now().isoformat()
                        
                        # Emitir vía WebSocket
                        socketio.emit('stats', current_stats, namespace='/ws')
                        last_mtime = stat.st_mtime
            
            time.sleep(0.5)
        except Exception as e:
            time.sleep(1)

def update_uptime():
    """Actualiza uptime cada 5 segundos"""
    while True:
        current_stats['uptime'] = int(time.time() - start_time)
        socketio.emit('uptime', {'ts': current_stats['uptime']}, namespace='/ws')
        time.sleep(5)

@app.route('/')
def index():
    """Página principal del dashboard"""
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    """API REST para obtener estadísticas"""
    return jsonify(current_stats)

@app.route('/api/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'ok',
        'uptime': current_stats['uptime'],
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/raw')
def api_raw():
    """Endpoint para archivo JSON crudo"""
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r') as f:
            return f.read(), 200, {'Content-Type': 'application/json'}
    return ('', 204)

@socketio.on('connect', namespace='/ws')
def handle_connect():
    """Cliente WebSocket conectado"""
    print('🔌 Cliente conectado')
    emit('stats', current_stats)

@socketio.on('disconnect', namespace='/ws')
def handle_disconnect():
    """Cliente WebSocket desconectado"""
    print('🔌 Cliente desconectado')

if __name__ == '__main__':
    # Crear directorio templates
    os.makedirs('templates', exist_ok=True)
    
    # Iniciar threads
    json_thread = threading.Thread(target=read_json_data, daemon=True)
    json_thread.start()
    
    uptime_thread = threading.Thread(target=update_uptime, daemon=True)
    uptime_thread.start()
    
    print("=" * 60)
    print("🛰️  GNSS.AI Dashboard Server v3.0 - ML Enhanced")
    print("=" * 60)
    print(f"📊 Dashboard: http://0.0.0.0:5000")
    print(f"📡 API REST:  http://0.0.0.0:5000/api/stats")
    print(f"💾 Data File: {JSON_FILE}")
    print("=" * 60)
    print("✅ Servidor iniciado. Ctrl+C para detener.")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
