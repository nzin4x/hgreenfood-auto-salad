import os
import json
import requests
from datetime import datetime, timedelta

# 캐시 파일 경로
CACHE_FILE = "holidays_cache.json"

# 공공 API에서 월별 휴일 데이터 가져오기
def fetch_holidays_from_api(year: int, month: int) -> list:
    API_URL = "https://api.publicholidays.com/{year}/{month}"  # 가짜 API URL, 실제 URL로 변경 필요
    response = requests.get(API_URL.format(year=year, month=month))
    response.raise_for_status()  # 요청 실패 시 예외 발생
    data = response.json()  # API 응답은 JSON 형식이라고 가정
    return [item['date'] for item in data.get('holidays', [])]

# 캐시 파일에서 데이터 읽기
def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# 캐시 파일에 데이터 저장
def save_cache(data):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 캐시에서 월별 휴일 데이터 가져오기
def get_cached_holidays(year: int, month: int) -> list:
    cache = load_cache()
    key = f"{year}-{month:02d}"
    return cache.get(key, [])

# 캐시에 월별 휴일 데이터 저장
def cache_holidays(year: int, month: int, holidays: list):
    cache = load_cache()
    key = f"{year}-{month:02d}"
    cache[key] = holidays
    save_cache(cache)

# 월별 휴일 데이터 갱신
def update_holidays_cache():
    today = datetime.now()
    year, month = today.year, today.month

    # 캐시 확인
    cached_holidays = get_cached_holidays(year, month)
    if not cached_holidays:
        print(f"휴일 데이터 없음. {year}-{month:02d} 데이터 갱신 중...")
        holidays = fetch_holidays_from_api(year, month)
        cache_holidays(year, month, holidays)
        print(f"{year}-{month:02d} 휴일 데이터 갱신 완료.")
    else:
        print(f"{year}-{month:02d} 휴일 데이터가 이미 캐시에 있습니다.")

# 특정 날짜가 휴일인지 확인
def is_holiday(date: datetime) -> bool:
    holidays = get_cached_holidays(date.year, date.month)
    return date.strftime("%Y-%m-%d") in holidays

# 예약 로직 예제
def schedule_next_day():
    today = datetime.now()
    tomorrow = today + timedelta(days=1)

    # 주말 또는 휴일 확인
    if tomorrow.weekday() >= 5 or is_holiday(tomorrow):
        print(f"{tomorrow.strftime('%Y-%m-%d')}은 예약하지 않습니다. (주말 또는 휴일)")
    else:
        print(f"{tomorrow.strftime('%Y-%m-%d')}에 예약합니다.")

# 실행
if __name__ == "__main__":
    update_holidays_cache()
    schedule_next_day()
