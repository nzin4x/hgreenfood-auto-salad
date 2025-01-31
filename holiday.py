from datetime import datetime, timedelta

import requests
from tinydb import TinyDB, Query

from config import DB_FILE, HOLIDAY_TBL_NM
from util import load_yaml

# TinyDB 설정
db = TinyDB(DB_FILE)
holiday_tbl = db.table(HOLIDAY_TBL_NM)

class Holiday:
    def __init__(self, config):
        self.config = config

    def fetch_holidays(self, year: int, month: int):
        params = {
            'serviceKey': self.config['data.go.kr']['api']['key'],
            'pageNo': '1',
            'numOfRows': '10',
            'solYear': str(year),
            'solMonth': str(month).zfill(2)
        }

        response = requests.get(self.config['data.go.kr']['api']['holiday']['endpoint'], params=params)
        import xml.etree.ElementTree as ET
        xml_data = response.content
        root = ET.fromstring(xml_data)

        locdates = [item.find('locdate').text for item in root.findall('.//item')]
        return locdates

    def cache_holidays(self, year: int, month: int, holidays: list):
        key = f"{year}{month:02d}"
        now = datetime.now().strftime("%Y-%m-%d")
        holiday_tbl.upsert({"key": key, "holidays": holidays, "last_updated": now}, Query().key == key)

    def get_cached_holidays(self, year: int, month: int):
        key = f"{year}{month:02d}"
        result = holiday_tbl.get(Query().key == key)
        if result:
            return result.get("holidays", []), result.get("last_updated", None)
        return [], None

    def update_holidays_cache(self, year: int, month: int):
        ''' 2달치의 정보를 수신한다. '''
        for offset in range(2):  # 현재 월과 다음 월 처리
            target_year = year
            target_month = month + offset
            if target_month > 12:
                target_year += 1
                target_month -= 12

            key = f"{target_year}{target_month:02d}"
            cached_holidays, last_updated = self.get_cached_holidays(target_year, target_month)

            if last_updated:
                last_updated_date = datetime.strptime(last_updated, "%Y-%m-%d")
                if last_updated_date >= datetime.now() - timedelta(weeks=1):
                    print(f"{key} 휴일 데이터가 최근 업데이트됨: {last_updated}, 갱신 불필요")
                    continue

            print(f"{key} 휴일 데이터 갱신 중...")
            holidays = self.fetch_holidays(target_year, target_month)
            self.cache_holidays(target_year, target_month, holidays)
            print(f"{key} 휴일 데이터 갱신 완료.")

    def 다음_근무일(self, 날짜):
        현재날짜 = datetime.strptime(날짜, '%Y%m%d')
        지금 = datetime.now()  # 현재 날짜와 시간을 가져옵니다.

        # 현재 시간이 13시 이전인지 확인합니다.
        if 지금.hour < 13:
            조건날짜 = 현재날짜  # 오늘 날짜를 기준으로 합니다.
        else:
            조건날짜 = 현재날짜 + timedelta(days=1)  # 내일 날짜를 기준으로 합니다.

        while True:
            year, month = 조건날짜.year, 조건날짜.month
            holidays, _ = self.get_cached_holidays(year, month)

            # 평일(월요일~금요일이고, 휴일이 아닐 경우) 확인
            if 조건날짜.weekday() < 5 and 조건날짜.strftime('%Y%m%d') not in holidays:
                break

            조건날짜 += timedelta(days=1)  # 다음 날로 이동

        print(f"다음 근무일 {조건날짜}")
        return 조건날짜.strftime('%Y%m%d')

# API URL
config = load_yaml('config.user.yaml')

if __name__ == '__main__':
    year = 2025
    month = 1

    holiday = Holiday(config)
    holiday.update_holidays_cache(year, month)
    holidays = holiday.get_cached_holidays(year, month)[0]

    print(holidays)


