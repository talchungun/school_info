import requests
from bs4 import BeautifulSoup
from datetime import datetime

# 오늘 날짜 문자열
def get_today_str():
    return datetime.today().strftime("%Y%m%d")

# 특정 날짜 급식 가져오기
def get_meal_by_date(date):
    url = f"https://school.use.go.kr/hcu-h/M01080101/list?ymd={date}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"}

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    selectors = {
        "조식": "#usm-content-body-id > ul.tch-lnc-list > li:nth-child(1) > dl > dd.tch-lnc > ul",
        "중식": "#usm-content-body-id > ul.tch-lnc-list > li:nth-child(2) > dl > dd.tch-lnc > ul",
        "석식": "#usm-content-body-id > ul.tch-lnc-list > li:nth-child(3) > dl > dd.tch-lnc > ul",
    }

    meals = {}

    for key, selector in selectors.items():
        block = soup.select_one(selector)
        if block:
            meals[key] = [li.get_text(strip=True) for li in block.select("li")]
        else:
            meals[key] = []  # 해당 급식이 없으면 빈 배열로

    return meals

# 오늘 급식만 반환
def get_today_meal():
    today = get_today_str()
    return get_meal_by_date(today)
