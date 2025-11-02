# -*- coding: utf-8 -*-
import json
import logging
import time
import traceback
import getpass
import os
import sys
from datetime import datetime, timedelta

import requests
from tinydb import TinyDB, Query

from config import DB_FILE, RESERVATION_HISTORY_TBL_NM
from holiday import Holiday
from util import load_yaml, merge_configs, already_done

VACATION_TBL_NM = 'vacation'

# SSL 경고 무시
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 로거 생성
logger = logging.getLogger("my_logger")
logger.setLevel(logging.DEBUG)  # 로그 레벨 설정 (DEBUG 이상 모두 기록)

# 1️⃣ 파일 핸들러 설정 (로그를 파일에 저장)
file_handler = logging.FileHandler("app.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)  # 파일에는 DEBUG 이상 저장

# 2️⃣ 콘솔 핸들러 설정 (로그를 콘솔에 출력)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # 콘솔에는 INFO 이상 출력

# 3️⃣ 로그 포맷 설정
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 4️⃣ 핸들러를 로거에 추가
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 전역 세션 객체 (로그인 세션 재사용)
session = requests.Session()

def save_cookies(cookies, filename):
    with open(filename, 'w') as cookie_file:
        for cookie in cookies:
            cookie_file.write(f"{cookie.name}={cookie.value}\n")


def 로그인(merged_config, force=False):
    """로그인 수행 (force=True일 때만 강제 재로그인)"""
    # 이미 쿠키 파일이 있고 force가 아니면 기존 세션 사용
    import os
    if not force and os.path.exists('cookies.txt'):
        logger.info("기존 로그인 세션 재사용")
        cookies = load_cookies('cookies.txt')
        for name, value in cookies.items():
            session.cookies.set(name, value)
        return True
    
    url = "https://hcafe.hgreenfood.com/api/com/login.do"
    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "userId": merged_config["userId"],
        "userData": merged_config["userData"],
        "osDvCd": merged_config["osDvCd"],
        "userCurrAppVer": merged_config["userCurrAppVer"],
        "mobiPhTrmlId": merged_config["mobiPhTrmlId"]
    }

    response = session.post(url, headers=headers, data=json.dumps(payload), verify=False)

    if json.loads(response.content)['errorCode'] == 0:
        logger.info("로그인 성공")
        save_cookies(response.cookies, 'cookies.txt')
        return True
    else:
        logger.error(f"로그인 실패: {response.status_code}, {response.text}")
        return False


def load_cookies(filename):
    cookies = {}
    with open(filename, 'r', encoding='utf-8') as cookie_file:
        for line in cookie_file:
            if line.strip():
                name, value = line.strip().split('=', 1)
                cookies[name] = value
    return cookies


def 예약주문요청(config, conerDvCd, prvdDt):
    """예약 주문 요청"""
    url = "https://hcafe.hgreenfood.com/api/menu/reservation/insertReservationOrder.do"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }

    payload = {
        "bizplcCd": config["bizplcCd"],
        "conerDvCd": conerDvCd,
        "mealDvCd": config["mealDvCd"],
        "prvdDt": prvdDt,
        "rownum": config["rownum"],
        "dlvrPlcFloorNo": config["dlvrPlcFloorNo"],
        "alphabetSeq": config["alphabetSeq"],
        "dlvrPlcFloorSeq": config["dlvrPlcFloorSeq"],
        "remainDeliQty": config["remainDeliQty"],
        "dlvrPlcNm": config["dlvrPlcNm"],
        "ordQty": config["ordQty"],
        "totalCount": config["totalCount"],
        "floorNm": config["floorNm"],
        "maxDelvQty": config["maxDelvQty"],
        "dlvrPlcSeq": config["dlvrPlcSeq"],
        "dlvrRsvDvCd": config["dlvrRsvDvCd"],
        "dsppUseYn": config["dsppUseYn"]
    }

    response = session.post(url, headers=headers, data=json.dumps(payload), verify=False)

    logger.info(f"예약 응답 코드: {response.status_code}")
    logger.debug(f"예약 응답 내용: {response.json()}")

    return response


def 예약조회요청(prvdDt, bizplcCd="196274"):
    """예약 목록 조회"""
    url = "https://hcafe.hgreenfood.com/api/menu/reservation/selectMenuReservationList.do"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }

    payload = {
        "prvdDt": prvdDt,
        "bizplcCd": bizplcCd
    }

    response = session.post(url, headers=headers, data=json.dumps(payload), verify=False)

    logger.debug(f"예약 조회 응답 코드: {response.status_code}")
    
    result = response.json()
    if result.get('errorCode') == 0:
        datasets = result.get('dataSets', {})
        reservations = datasets.get('reserveList', [])
        logger.debug(f"예약 조회 결과: {len(reservations)}건")
        return reservations
    
    return []


def show_current_reservations(prvdDt):
    """현재 예약 현황 출력 (단일 날짜)"""
    logger.info("\n" + "="*60)
    logger.info("📋 다음 예약 대상일 확인")
    logger.info("="*60)
    
    reservations = 예약조회요청(prvdDt)
    if reservations:
        # 중복 제거 및 표시
        shown_menus = set()
        for res in reservations:
            menu_name = res.get('conerNm', '알 수 없음')
            date = res.get('prvdDt', '')
            menu_key = f"{date}:{menu_name}"
            
            if menu_key not in shown_menus:
                shown_menus.add(menu_key)
                # 날짜 포맷팅 (YYYYMMDD -> YYYY-MM-DD)
                if len(date) == 8:
                    formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
                else:
                    formatted_date = date
                logger.info(f"✅ {formatted_date}: {menu_name} - 이미 예약 완료")
    else:
        # 날짜 포맷팅
        if len(prvdDt) == 8:
            formatted_date = f"{prvdDt[:4]}-{prvdDt[4:6]}-{prvdDt[6:]}"
        else:
            formatted_date = prvdDt
        logger.info(f"📌 {formatted_date}: 아직 예약 안 됨 → 예약 대기 중")
    
    logger.info("="*60 + "\n")


def 예약취소요청(reservation_data):
    """예약 취소 요청 - 예약 데이터 전체를 받아서 취소"""
    url = "https://hcafe.hgreenfood.com/api/menu/reservation/updateMenuReservationCancel.do"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }

    # 예약 데이터를 그대로 사용
    payload = reservation_data

    response = session.post(url, headers=headers, data=json.dumps(payload), verify=False)

    logger.info(f"취소 응답 코드: {response.status_code}")
    logger.debug(f"취소 응답 내용: {response.json()}")

    return response


menu_corner_map = {
    "샌": "0005",
    "샐": "0006",
    "빵": "0007",
    "헬": "0009",
    "닭": "0010"
}


def reserve(merged_config, prvdDt, login_once=False):
    """
    예약 시도
    login_once: True면 세션 재사용, False면 매번 로그인
    """
    if not login_once:
        if not 로그인(merged_config):
            return False, "로그인 실패"

    menuSeq = merged_config['menuSeq']
    menuInitials = [corner.strip() for corner in menuSeq.split(",")]

    db = TinyDB(DB_FILE, ensure_ascii=False, encoding='utf-8')
    reserve_his_tbl = db.table(RESERVATION_HISTORY_TBL_NM)

    reserveOK = False
    reason = ""

    for menuInitial in menuInitials:
        conerDvCd = menu_corner_map.get(menuInitial.strip())

        if conerDvCd:
            response = 예약주문요청(merged_config, conerDvCd, prvdDt)

            log_entry = {
                "date": prvdDt,
                "requested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "menu": conerDvCd,
                "menu_name": menuInitial,
                "status_code": response.status_code,
                "errorCode": response.json().get('errorCode'),
                "errorMsg": response.json().get('errorMsg')
            }

            if response.status_code == 200 and response.json().get('errorCode') == 0:
                logger.info(f"✅ {prvdDt} 에 {menuInitial} 예약 성공!")
                reserveOK = True
                reason = f"{menuInitial} 예약 성공"
                log_entry.update({"reserveOk": True})
                reserve_his_tbl.insert(log_entry)
                break
            elif already_done(response):
                logger.info(f"ℹ️ {prvdDt} 에 이미 다른 메뉴가 예약되어 있음")
                reserveOK = True
                reason = "이미 예약됨"
                log_entry.update({"reserveOk": True})
                reserve_his_tbl.insert(log_entry)
                break
            else:
                # 해당 메뉴 실패 - 다음 메뉴 시도
                error_msg = response.json().get('errorMsg', '알 수 없는 오류')
                logger.warning(f"⚠️ {menuInitial} 예약 실패: {error_msg}")
                log_entry.update({"reserveOk": False})
                reserve_his_tbl.insert(log_entry)
                reason = f"모든 메뉴 실패"

    return reserveOK, reason


def load_config_with_password():
    """설정 파일 로드 (암호화된 경우 마스터 패스워드 입력)"""
    if not os.path.exists('config.user.yaml'):
        logger.error("설정 파일이 없습니다. 'python setup_config.py'를 먼저 실행하세요.")
        sys.exit(1)
    
    import yaml
    with open('config.user.yaml', 'r', encoding='utf-8') as f:
        user_config = yaml.safe_load(f)
    
    # 암호화된 설정인 경우
    if user_config.get('_encrypted'):
        print("\n🔐 암호화된 설정 파일입니다.")
        
        # Windows에서는 IME를 영문으로 전환 시도 (최선 시도)
        try:
            from util import set_ime_english
            set_ime_english()
            print("   (입력 전 한/영키를 영문으로 전환 시도했습니다)")
        except Exception:
            pass

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            master_password = getpass.getpass(f"마스터 패스워드를 입력하세요 ({attempt}/{max_attempts}): ")
            
            from setup_config import load_and_decrypt_config
            decrypted_config = load_and_decrypt_config(master_password)
            
            if decrypted_config:
                print("✅ 설정 파일 로드 완료\n")
                return decrypted_config
            else:
                if attempt < max_attempts:
                    print(f"❌ 마스터 패스워드가 올바르지 않습니다. (남은 시도: {max_attempts - attempt}회)")
                else:
                    logger.error("❌ 마스터 패스워드 입력 실패 횟수 초과. 프로그램을 종료합니다.")
                    sys.exit(1)
    
    # 구 버전 (암호화되지 않은 설정)
    return user_config


def main():
    try:
        print("\n" + "="*60)
        print("🍽️ 사내 식당 자동 예약 프로그램")
        print("="*60)
        
        # 설정 파일 로드
        user_config = load_config_with_password()
        default_config = load_yaml('config.default.yaml')
        merged_config = merge_configs(default_config, user_config)

        holiday = Holiday(merged_config)
        holiday.update_holidays_cache(datetime.today().year, datetime.today().month)
        
        # 초기 로그인 1회만 수행
        if not 로그인(merged_config):
            logger.error("초기 로그인 실패. 프로그램 종료")
            return
        
        # 현재 예약 현황 조회 (다음 근무일만)
        now = datetime.now()
        today = now.strftime('%Y%m%d')
        next_workday = holiday.다음_근무일(today)
        show_current_reservations(next_workday)

        while True:
            now = datetime.now()
            today = now.strftime('%Y%m%d')
            
            # 휴일 캐시 업데이트 (매월 1일에)
            if now.day == 1:
                holiday.update_holidays_cache(now.year, now.month)
            
            cached_holidays = holiday.get_cached_holidays(now.year, now.month)[0]
            
            # 다음 예약 대상 날짜 계산
            prvdDt = holiday.다음_근무일(today)
            
            logger.info(f"현재 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}, 예약 대상일: {prvdDt}")

            # DB 연결
            db = TinyDB(DB_FILE, ensure_ascii=False, encoding='utf-8')
            reserve_his_tbl = db.table(RESERVATION_HISTORY_TBL_NM)
            vacation_tbl = db.table(VACATION_TBL_NM)
            
            # 휴가 날짜 확인
            vacation_dates = vacation_tbl.search(Query().date == prvdDt)
            if vacation_dates:
                vacation = vacation_dates[0]
                reason = vacation.get('reason', '휴가')
                logger.info(f"🏖️ {prvdDt}는 예약 금지 날짜입니다 ({reason}). 다음 근무일로 이동")
                # 다음 근무일 계산 (휴가 날짜 건너뛰기)
                next_date = datetime.strptime(prvdDt, '%Y%m%d') + timedelta(days=1)
                sleep_until_next_workday_noon(next_date.strftime('%Y%m%d'), merged_config)
                continue
            
            # 이미 예약 완료 여부 확인
            already_reserved = reserve_his_tbl.search(
                (Query().date == prvdDt) & (Query().reserveOk == True)
            )
            
            if already_reserved:
                logger.info(f"{prvdDt} 이미 예약 완료. 다음 근무일까지 대기")
                sleep_until_next_workday_noon(prvdDt, merged_config)
                continue
            
            # 예약 시간 계산
            reservation_time = now.replace(
                hour=merged_config["reserve"]["at"]["hour"],
                minute=merged_config["reserve"]["at"]["minute"],
                second=merged_config["reserve"]["at"]["second"],
                microsecond=0
            )
            
            # 오늘이 휴일이거나 주말이면 다음 근무일까지 대기
            if today in cached_holidays or now.weekday() >= 5:
                logger.info(f"오늘은 휴일/주말. 다음 근무일 {prvdDt}까지 대기")
                sleep_until_next_workday_noon(prvdDt, merged_config)
                continue
            
            # 예약 시간 체크
            time_until_reservation = (reservation_time - now).total_seconds()
            
            if time_until_reservation > 60:
                # 예약 시간까지 1분 이상 남음 - 대기
                logger.info(f"예약 시간까지 {time_until_reservation}초 대기")
                time.sleep(min(time_until_reservation - 60, 3600))  # 최대 1시간씩 대기
                continue
            
            elif -5 < time_until_reservation <= 60:
                # 예약 시간 5초 전부터 1분 후까지 - 예약 시도
                logger.info("⏰ 예약 시간 도달! 예약 시도 시작")
                
                max_retries = merged_config.get("max_retry", 10)
                retry_interval = merged_config.get("retry_interval", 5)
                
                retry_count = 0
                success = False
                
                while retry_count < max_retries:
                    retry_count += 1
                    logger.info(f"🔄 예약 시도 {retry_count}/{max_retries}")
                    
                    # 세션 재사용하여 예약 시도
                    result, reason = reserve(merged_config, prvdDt, login_once=True)
                    
                    if result:
                        if "이미 예약됨" in reason:
                            logger.info(f"ℹ️ {reason} - 더 이상 시도 불필요")
                            success = True
                            break
                        else:
                            logger.info(f"✅ {reason}")
                            success = True
                            break
                    else:
                        logger.warning(f"⚠️ 예약 실패 ({reason})")
                    
                    # 마지막 시도가 아니면 대기
                    if retry_count < max_retries:
                        time.sleep(retry_interval)
                
                if not success:
                    logger.error(f"❌ {max_retries}회 시도 후 모든 메뉴 예약 실패")
                
                # 예약 시도 완료 후 다음 근무일까지 대기
                sleep_until_next_workday_noon(prvdDt, merged_config)
            
            else:
                # 예약 시간이 1분 이상 지남 - 다음 근무일로
                logger.warning(f"예약 시간({reservation_time}) 지남. 다음 근무일로 이동")
                sleep_until_next_workday_noon(prvdDt, merged_config)

    except Exception as e:
        logger.error(f"에러 발생: {e}")
        logger.error(traceback.format_exc())  # 전체 Stack Trace 출력


def sleep_until_next_workday_noon(prvdDt, merged_config):
    """다음 예약 시간까지 대기"""
    next_workday = datetime.strptime(prvdDt, '%Y%m%d')
    target_time = next_workday.replace(
        hour=merged_config["reserve"]["at"]["hour"],
        minute=merged_config["reserve"]["at"]["minute"],
        second=merged_config["reserve"]["at"]["second"],
        microsecond=0
    )

    current_time = datetime.now()
    sleep_duration = (target_time - current_time).total_seconds()

    logger.debug(f"현재={current_time}, 목표={target_time}, 대기시간={sleep_duration}초")

    if sleep_duration <= 0:
        logger.warning(f"목표 시간이 과거입니다. 10초 후 재시작")
        sleep_duration = 10

    # 날짜 포맷팅
    formatted_date = f"{prvdDt[:4]}-{prvdDt[4:6]}-{prvdDt[6:]}"
    
    # 예약 상태 확인
    reservations = 예약조회요청(prvdDt)
    if reservations:
        logger.info(f"✅ {formatted_date} 예약 완료 → 다음 근무일 예약을 위해 대기")
    else:
        logger.info(f"📌 {formatted_date} 예약 예정 → 예약 시간까지 대기")
    
    logger.info(f"⏰ 다음 예약 시간: {target_time.strftime('%Y-%m-%d %H:%M:%S')} ({sleep_duration/3600:.1f}시간 후)")
    time.sleep(sleep_duration)

if __name__ == '__main__':
    main()
