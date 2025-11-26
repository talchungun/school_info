import requests
from bs4 import BeautifulSoup
from datetime import datetime

def get_schedule():
    from datetime import datetime
    import requests
    from bs4 import BeautifulSoup

    year = datetime.now().year
    month = datetime.now().month

    url = f"https://school.use.go.kr/hcu-h/M01040401/list?y={year}&m={month}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    items = soup.select("#usm-content-body-id > ul > li")
    schedule_list = []

    for li in items:
        text = li.get_text(strip=True)
        if text and "-" in text:
            date_str, title = text.split("-", 1)
            schedule_list.append({
                "date": date_str.strip(),
                "title": title.strip()
            })

    return schedule_list