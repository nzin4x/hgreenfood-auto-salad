import json
import os
from datetime import datetime, timedelta

import requests
from tinydb import TinyDB, Query
from util import load_yaml

# TinyDB 설정
DB_FILE = "data.json"
db = TinyDB(DB_FILE)
HolidayTable = db.table('holiday')

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
        HolidayTable.upsert({"key": key, "holidays": holidays, "last_updated": now}, Query().key == key)

    def get_cached_holidays(self, year: int, month: int):
        key = f"{year}{month:02d}"
        result = HolidayTable.get(Query().key == key)
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
        다음날짜 = 현재날짜 + timedelta(days=1)

        while True:
            year, month = 다음날짜.year, 다음날짜.month
            holidays, _ = self.get_cached_holidays(year, month)
            if 다음날짜.weekday() < 5 and 다음날짜.strftime('%Y%m%d') not in holidays:
                break
            다음날짜 += timedelta(days=1)

        print(f"다음 근무일 {다음날짜}")
        return 다음날짜.strftime('%Y%m%d')

# API URL
config = load_yaml('config.user.yaml')

if __name__ == '__main__':
    year = 2025
    month = 1

    holiday = Holiday(config)
    holiday.update_holidays_cache(year, month)
    holidays = holiday.get_cached_holidays(year, month)[0]

    print(holidays)


