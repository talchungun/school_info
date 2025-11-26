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
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30) 
Session(app)

cached_meal = None
cached_schedule = None
cached_notice = None
cached_dday = None

#공지사항 로드/저장 함수

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

#급식, 일정 업데이트 함수

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
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


def load_dday():
    global cached_dday
    file_path = "data/dday.json"
    
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                cached_dday = json.load(f)
            print("[UPDATE] D-Day data loaded from file.")
        except Exception as e:
            print(f"[ERROR] D-Day file exists but failed to load: {e}. Keeping existing cached_dday.")
    
    if cached_dday is None:
        cached_dday = {"target_date": date.today().strftime("%Y-%m-%d"), "target_name": "목표 설정 필요"}
        print("[INIT] D-Day initialized with default values.")

def save_dday(target_date, target_name):
    global cached_dday
    cached_dday = {"target_date": target_date, "target_name": target_name}
    os.makedirs("data", exist_ok=True)
    with open("data/dday.json", "w", encoding="utf-8") as f:
        json.dump(cached_dday, f, ensure_ascii=False, indent=2)


def calculate_dday_data():
    global cached_dday
    if not cached_dday:
        return {"dday_info": None, "dday_count": None}
        
    target_date_str = cached_dday["target_date"]
    dday_count = None
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        today = date.today()
        delta = target_date - today
        dday_count = delta.days
    except Exception:
        dday_count = None
    
    return {
        "dday_info": cached_dday,
        "dday_count": dday_count
    }

#메인 페이지

@app.route("/")
def index():

    dday_data = calculate_dday_data()

    return render_template(
        "index.html",
        meal=cached_meal,
        schedule=cached_schedule,
        notices=cached_notice["notices"],
        dday_info=dday_data["dday_info"],
        dday_count=dday_data["dday_count"]
    )

#api

@app.route("/api/meal")
def api_meal():
    return jsonify(cached_meal)

@app.route("/api/dday")
def api_dday():
    data = calculate_dday_data()
    return jsonify(data)

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

    #이거 가끔씩 크롤링 해올 때 날짜가 25.12.04-26.01.15 이런식으로 오는 경우가 있어서 처리하려고 만듦

    for item in cached_schedule:
        d_str = item.get("date") if isinstance(item, dict) else None
        if not d_str:
            filtered.append(item)
            continue

        parsed_start = None
        parsed_end = None

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

#관리자 페이지

@app.route("/admin/delete_notice/<int:notice_index>", methods=["POST"])
@requires_auth
def delete_notice_route(notice_index):
    notices = cached_notice.get("notices", [])
    
    if 0 <= notice_index < len(notices):
        deleted_notice = notices.pop(notice_index)
        save_notice(notices)
        print(f"[ADMIN] Notice deleted: Index {notice_index}, Content: {deleted_notice}")
    else:
        print(f"[ADMIN ERROR] Invalid notice index for deletion: {notice_index}")
        
    return redirect(url_for("admin_page"))

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if check_auth(username, password):
            session['admin_logged_in'] = True
            session.permanent = True
            app.permanent_session_lifetime = timedelta(minutes=30)
            return redirect(url_for("admin_page"))
        else:
            return render_template("admin/login.html", error="아이디 또는 비밀번호가 틀렸습니다.")
    
    return render_template("admin/login.html")


@app.route("/admin/save_dday", methods=["POST"])
@requires_auth
def save_dday_route():
    target_date = request.form.get("target_date")
    target_name = request.form.get("target_name")
    
    if target_date and target_name:
        try:
            datetime.strptime(target_date, "%Y-%m-%d")
            save_dday(target_date, target_name)
            print(f"[ADMIN] D-Day set: {target_name} on {target_date}")
        except ValueError:
            pass 
            
    return redirect(url_for("admin_page"))

@app.route("/admin")
@requires_auth
def admin_page():
    now = date.today()
    notices_with_index = []
    
    for index, n in enumerate(cached_notice.get("notices", [])):
        is_visible = False
        
        if isinstance(n, str):
            is_visible = True
            item_data = {"text": n, "index": index}
        elif isinstance(n, dict):
            expires = n.get("expires_at")
            
            if not expires:
                is_visible = True
            else:
                try:
                    exp_dt = datetime.strptime(expires, "%Y-%m-%d").date()
                    if exp_dt >= now:
                        is_visible = True
                except Exception:
                    is_visible = True
            
            if is_visible:
                item_data = n.copy()
                item_data["index"] = index 
                
        if is_visible:
            notices_with_index.append(item_data)

    current_dday = cached_dday
    
    return render_template(
        "admin/index.html", 
        notices=notices_with_index,
        current_dday=current_dday
    )
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

if __name__ == "__main__":
    update_meal()
    update_schedule()
    load_notice()
    load_dday() 

    scheduler = BackgroundScheduler()
    scheduler.add_job(update_meal, "cron", hour=0, minute=30)
    scheduler.add_job(update_schedule, "interval", hours=2)
    
    try:
        scheduler.start()
        print("[INIT] Background scheduler started.")
    except Exception as e:
        print(f"[ERROR] Scheduler failed to start: {e}")

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)