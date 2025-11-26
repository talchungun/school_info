from flask import Flask, render_template, jsonify, request, redirect, url_for, Response, session
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, date, timedelta
from flask_session import Session
import json
import os
import re
from functools import wraps

from crawlers.meal_crawler import get_meal_by_date
from crawlers.schedule_crawler import get_schedule

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # 30분 세션 유지
Session(app)

# -----------------------------
# 캐시 저장소
# -----------------------------
cached_meal = None
cached_schedule = None
cached_notice = None

# -----------------------------
# 공지사항 로드/저장 함수
# -----------------------------
def load_notice():
    global cached_notice
    try:
        with open("data/notice.json", "r", encoding="utf-8") as f:
            cached_notice = json.load(f)
    except:
        cached_notice = {"notices": []}

def save_notice(new_notices):
    global cached_notice
    cached_notice = {"notices": new_notices}
    os.makedirs("data", exist_ok=True)
    with open("data/notice.json", "w", encoding="utf-8") as f:
        json.dump(cached_notice, f, ensure_ascii=False, indent=2)

# -----------------------------
# 데이터 업데이트 함수
# -----------------------------
def update_meal():
    global cached_meal
    today = date.today().strftime("%Y%m%d")
    cached_meal = get_meal_by_date(today)
    print("[UPDATE] Meal data updated.")

def update_schedule():
    global cached_schedule
    cached_schedule = get_schedule()
    print("[UPDATE] Schedule data updated.")

ADMIN_USER = os.environ.get("ADMIN_USER", "test")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "1234")

def check_auth(username, password):
    return username == ADMIN_USER and password == ADMIN_PASS

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # 세션에 로그인 정보가 있는지 확인
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# -----------------------------
# 초기 데이터 로드
# -----------------------------
update_meal()
update_schedule()
load_notice()

# -----------------------------
# 스케줄러 — 1시간마다 갱신
# -----------------------------
scheduler = BackgroundScheduler()
scheduler.add_job(update_meal, "cron", hour=0, minute=30)
scheduler.add_job(update_schedule, "interval", hours=2)
scheduler.start()


# -----------------------------
# 기본 화면
# -----------------------------
@app.route("/")
def index():
    return render_template(
        "index.html",
        meal=cached_meal,
        schedule=cached_schedule,
        notices=cached_notice["notices"]
    )

# -----------------------------
# API 라우트
# -----------------------------
@app.route("/api/meal")
def api_meal():
    return jsonify(cached_meal)

@app.route("/api/schedule")
def api_schedule():
    if not cached_schedule:
        return jsonify([])

    today = date.today()
    five_days_later = today + timedelta(days=5)
    filtered = []
    fmts = ("%y.%m.%d", "%Y.%m.%d", "%y.%m.%d %H:%M", "%Y.%m.%d %H:%M",
            "%y-%m-%d", "%Y-%m-%d", "%y/%m/%d", "%Y/%m/%d")

    def conv_year(y):
        if y < 100:
            return y + 2000 if y <= 68 else y + 1900
        return y

    for item in cached_schedule:
        d_str = item.get("date") if isinstance(item, dict) else None
        if not d_str:
            filtered.append(item)
            continue

        parsed_start = None
        parsed_end = None

        # 숫자 조각으로 분석 (범위 예: '25.10.05~25.10.07', '25.10.05~07' 등)
        parts = [p for p in re.split(r"[^0-9]", d_str) if p]

        try:
            if len(parts) >= 6:
                y1, m1, d1, y2, m2, d2 = map(int, parts[:6])
                parsed_start = date(conv_year(y1), m1, d1)
                parsed_end = date(conv_year(y2), m2, d2)
            elif len(parts) == 5:
                y, m1, d1, m2, d2 = map(int, parts)
                parsed_start = date(conv_year(y), m1, d1)
                parsed_end = date(conv_year(y), m2, d2)
            elif len(parts) == 4:
                y, m, d1, d2 = map(int, parts)
                parsed_start = date(conv_year(y), m, d1)
                parsed_end = date(conv_year(y), m, d2)
            else:
                for f in fmts:
                    try:
                        parsed_start = datetime.strptime(d_str, f).date()
                        break
                    except Exception:
                        continue

                if parsed_start is None and len(parts) >= 3:
                    y, m, d = map(int, parts[:3])
                    parsed_start = date(conv_year(y), m, d)
        except Exception:
            parsed_start = None
            parsed_end = None

        if parsed_start is None:
            continue

        if parsed_end is None:
            parsed_end = parsed_start

        # 오늘부터 5일뒤까지 범위에 겹치는 일정만 포함
        # (범위의 끝이 today 이상이고, 범위의 시작이 five_days_later 이하)
        if parsed_end >= today and parsed_start <= five_days_later:
            filtered.append(item)

    return jsonify(filtered)

@app.route("/api/notice")
def api_notice():
    now = date.today()
    visible = []
    
    for n in cached_notice.get("notices", []):
        if isinstance(n, str):
            visible.append(n)
            continue

        if isinstance(n, dict):
            expires = n.get("expires_at")
            if not expires:
                visible.append(n)
                continue

            exp_dt = None
            try:
                exp_dt = datetime.strptime(expires, "%Y-%m-%d").date()
            except Exception:
                visible.append(n)
                continue

            if exp_dt >= now:
                visible.append(n)

    return jsonify({"notices": visible})

# -----------------------------
# 관리자 페이지
# -----------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if check_auth(username, password):
            session['admin_logged_in'] = True
            session.permanent = True  # 세션 유지
            app.permanent_session_lifetime = timedelta(minutes=30)
            return redirect(url_for("admin_page"))
        else:
            return render_template("admin/login.html", error="아이디 또는 비밀번호가 틀렸습니다.")
    
    return render_template("admin/login.html")

@app.route("/admin")
@requires_auth
def admin_page():
    now = date.today()
    visible_notices = []
    
    for n in cached_notice.get("notices", []):
        if isinstance(n, str):
            visible_notices.append(n)
            continue
        
        if isinstance(n, dict):
            expires = n.get("expires_at")
            if not expires:
                visible_notices.append(n)
                continue
            
            try:
                exp_dt = datetime.strptime(expires, "%Y-%m-%d").date()
            except Exception:
                visible_notices.append(n)
                continue
            
            print(exp_dt, now)
            if exp_dt >= now:
                visible_notices.append(n)
    
    cached_notice["notices"] = visible_notices
    save_notice(visible_notices)
    
    return render_template("admin/index.html", notices=visible_notices)

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

@app.route("/admin/save", methods=["POST"])
@requires_auth
def save_notice_route():
    new_notice = request.form.get("notice")
    expires_at = request.form.get("expires_at")
    if new_notice:
        notices = cached_notice.get("notices", [])
        if expires_at:
            notices.append({"text": new_notice, "expires_at": expires_at})
        else:
            notices.append(new_notice)
        save_notice(notices)
    return redirect(url_for("admin_page"))

@app.route("/notices")
def notices_page():
    # 서버 렌더링용 초기 데이터 전달(없어도 동작하나 편의상 전달)
    return render_template("notices.html", notices=cached_notice.get("notices", []))

# -----------------------------
# 서버 실행
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
