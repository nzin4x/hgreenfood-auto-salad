from datetime import datetime, timedelta

import requests
from tinydb import TinyDB, Query

from config import DB_FILE, HOLIDAY_TBL_NM
from util import load_yaml

# TinyDB 설정
db = TinyDB(DB_FILE, ensure_ascii=False, encoding='utf-8')
holiday_tbl = db.table(HOLIDAY_TBL_NM)


class Holiday:
    def __init__(self, config):
        self.config = config

    def fetch_holidays(self, year: int, month: int):
        # data.go.kr 샘플 코드와 동일하게 params 사용
        params = {
            'serviceKey': self.config['data.go.kr']['api']['key'],
            'solYear': str(year),
            'solMonth': str(month).zfill(2)
        }

        try:
            response = requests.get(self.config['data.go.kr']['api']['holiday']['endpoint'], params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"⚠️ 휴일 API 호출 실패 (상태 코드: {response.status_code})")
                print(f"   캐시된 데이터를 사용하거나 휴일 체크를 건너뜁니다.")
                return []
            
            import xml.etree.ElementTree as ET
            xml_data = response.content
            root = ET.fromstring(xml_data)
            
            # 에러 코드 확인
            result_code = root.find('.//resultCode')
            if result_code is not None and result_code.text != '00':
                result_msg = root.find('.//resultMsg')
                msg = result_msg.text if result_msg is not None else 'Unknown'
                print(f"⚠️ 휴일 API 오류 (코드: {result_code.text}, 메시지: {msg})")
                print(f"   캐시된 데이터를 사용하거나 휴일 체크를 건너뜁니다.")
                return []

            locdates = [item.find('locdate').text for item in root.findall('.//item')]
            return locdates
        except Exception as e:
            print(f"⚠️ 휴일 데이터 조회 중 오류 발생: {e}")
            print(f"   캐시된 데이터를 사용하거나 휴일 체크를 건너뜁니다.")
            return []

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
        updates_needed = []
        cache_status = []
        
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
                    cache_status.append(f"{key}(캐시)")
                    continue

            updates_needed.append((target_year, target_month, key))
        
        # 요약 메시지 출력
        if cache_status and not updates_needed:
            print(f"📅 휴일 캐시: {', '.join(cache_status)} - 갱신 불필요")
        
        # 갱신이 필요한 월만 처리
        for target_year, target_month, key in updates_needed:
            print(f"📅 {key} 휴일 데이터 갱신 중...")
            try:
                holidays = self.fetch_holidays(target_year, target_month)
                if holidays or holidays == []:  # 빈 리스트도 유효 (공휴일 없는 달)
                    self.cache_holidays(target_year, target_month, holidays)
                    if holidays:
                        print(f"✅ {key} 휴일 {len(holidays)}건 갱신 완료")
                    else:
                        print(f"✅ {key} 공휴일 없음")
            except Exception as e:
                print(f"⚠️ {key} 휴일 데이터 갱신 실패: {e}")
                print(f"   기존 캐시 데이터를 계속 사용합니다.")

    def get_next_action_date(self):
        """
        다음 예약 실행(기동) 날짜를 계산합니다.
        - 평일 13시 이전: 오늘 13시
        - 평일 13시 이후: 다음 평일 13시
        - 주말/휴일: 다음 평일 13시
        """
        now = datetime.now()
        today_str = now.strftime('%Y%m%d')
        
        # 오늘이 평일이고 휴일이 아닌지 확인
        year, month = now.year, now.month
        holidays, _ = self.get_cached_holidays(year, month)
        is_workday = now.weekday() < 5 and today_str not in holidays
        
        if is_workday and now.hour < 13:
            return today_str
        
        # 다음 평일 찾기
        next_date = now + timedelta(days=1)
        while True:
            year, month = next_date.year, next_date.month
            holidays, _ = self.get_cached_holidays(year, month)
            
            if next_date.weekday() < 5 and next_date.strftime('%Y%m%d') not in holidays:
                return next_date.strftime('%Y%m%d')
            
            next_date += timedelta(days=1)

    def get_target_service_date(self, action_date_str):
        """
        예약 실행 날짜(action_date)를 기준으로 예약할 식단 날짜(service_date)를 계산합니다.
        - 원칙: 예약 실행일의 '다음 근무일'
        """
        action_date = datetime.strptime(action_date_str, '%Y%m%d')
        next_date = action_date + timedelta(days=1)
        
        while True:
            year, month = next_date.year, next_date.month
            holidays, _ = self.get_cached_holidays(year, month)
            
            if next_date.weekday() < 5 and next_date.strftime('%Y%m%d') not in holidays:
                return next_date.strftime('%Y%m%d')
            
            next_date += timedelta(days=1)

    def get_nearest_future_workday(self):
        """
        오늘을 포함하여 가장 가까운 미래의 평일(근무일)을 찾습니다.
        - 오늘이 평일이면 오늘 반환
        - 오늘이 휴일이면 다음 평일 반환
        """
        now = datetime.now()
        date = now
        
        while True:
            year, month = date.year, date.month
            holidays, _ = self.get_cached_holidays(year, month)
            
            if date.weekday() < 5 and date.strftime('%Y%m%d') not in holidays:
                return date.strftime('%Y%m%d')
            
            date += timedelta(days=1)

    def get_previous_workday(self, date_str):
        """
        주어진 날짜의 바로 전 평일(근무일)을 찾습니다.
        """
        date = datetime.strptime(date_str, '%Y%m%d')
        date -= timedelta(days=1)
        
        while True:
            year, month = date.year, date.month
            holidays, _ = self.get_cached_holidays(year, month)
            
            if date.weekday() < 5 and date.strftime('%Y%m%d') not in holidays:
                return date.strftime('%Y%m%d')
            
            date -= timedelta(days=1)




# API URL
config = load_yaml('config.user.yaml')

if __name__ == '__main__':
    year = 2025
    month = 1

    holiday = Holiday(config)
    holiday.update_holidays_cache(year, month)
    holidays = holiday.get_cached_holidays(year, month)[0]

    print(holidays)
