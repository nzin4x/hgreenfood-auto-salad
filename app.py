# -*- coding: utf-8 -*-
import json
import logging
import time
import traceback
import getpass
import os
import sys
import threading
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


def check_session():
    """현재 세션이 유효한지 확인"""
    url = "https://hcafe.hgreenfood.com/api/menu/reservation/selectMenuReservationList.do"
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Accept": "application/json, text/javascript, */*; q=0.01"
    }
    # 오늘 날짜로 조회 시도
    payload = {
        "prvdDt": datetime.now().strftime('%Y%m%d'),
        "bizplcCd": "196274"
    }
    
    try:
        response = session.post(url, headers=headers, data=json.dumps(payload), verify=False, timeout=5)
        if response.status_code == 200:
            try:
                # 응답이 JSON이고 errorCode가 있으면 세션 유효
                res = response.json()
                if res.get('errorCode') == 0:
                    return True
            except:
                pass
        return False
    except:
        return False


def 로그인(merged_config, force=False):
    """로그인 수행 (force=True일 때만 강제 재로그인)"""
    # 이미 쿠키 파일이 있고 force가 아니면 기존 세션 사용 시도
    import os
    if not force and os.path.exists('cookies.txt'):
        logger.debug("기존 쿠키 로드 및 세션 확인...")
        cookies = load_cookies('cookies.txt')
        for name, value in cookies.items():
            session.cookies.set(name, value)
            
        # 세션 유효성 검사
        if check_session():
            logger.info("   기존 세션 유효함")
            return True
        else:
            logger.info("   기존 세션 만료됨 - 재로그인 필요")
    
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

    logger.info(f"🌐 API 호출: login.do (사용자: {merged_config['userId']})")

    try:
        response = session.post(url, headers=headers, data=json.dumps(payload), verify=False, timeout=10)
        logger.info(f"   응답 상태: {response.status_code}")

        if response.status_code == 200 and json.loads(response.content)['errorCode'] == 0:
            logger.info("   로그인 성공")
            save_cookies(response.cookies, 'cookies.txt')
            return True
        else:
            logger.error(f"   로그인 실패: {response.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"   로그인 중 오류: {e}")
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
        "Content-Type": "application/json; charset=UTF-8",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://hcafe.hgreenfood.com/ctf/menu/reservation/menuReservation.do",
        "Origin": "https://hcafe.hgreenfood.com"
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

    logger.info(f"🌐 API 호출: insertReservationOrder.do")
    logger.info(f"   요청 파라미터: prvdDt={prvdDt}, conerDvCd={conerDvCd}")

    response = session.post(url, headers=headers, data=json.dumps(payload), verify=False, timeout=10)

    logger.info(f"   응답 상태: {response.status_code}")
    try:
        resp_json = response.json()
        logger.info(f"   응답 내용: errorCode={resp_json.get('errorCode')}, errorMsg={resp_json.get('errorMsg')}")
    except:
        logger.warning(f"   응답 본문 (JSON 파싱 실패): {response.text[:500]}")

    return response


def 예약조회요청(prvdDt, bizplcCd="196274", retry_on_auth_fail=True):
    """예약 목록 조회
    
    prvdDt: 제공일(배달일) - 요청 파라미터이자 응답의 prvdDt 필드
    rsvDt: 예약일 - 응답의 rsvDt 필드
    rsvStatCd: 예약 상태 코드 ('A' = 예약 완료)
    retry_on_auth_fail: 401/403 오류 시 재로그인 후 재시도 여부
    
    주의: 서버는 요청한 prvdDt뿐만 아니라 다른 날짜의 예약도 함께 반환할 수 있음
    """
    url = "https://hcafe.hgreenfood.com/api/menu/reservation/selectMenuReservationList.do"
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://hcafe.hgreenfood.com/ctf/menu/reservation/menuReservation.do",
        "Origin": "https://hcafe.hgreenfood.com"
    }

    payload = {
        "prvdDt": str(prvdDt) if not isinstance(prvdDt, str) else prvdDt,
        "bizplcCd": bizplcCd
    }

    # API 호출 로그
    logger.info(f"🌐 API 호출: selectMenuReservationList.do")
    logger.info(f"   요청 파라미터: prvdDt={payload['prvdDt']}, bizplcCd={payload['bizplcCd']}")

    try:
        response = session.post(url, headers=headers, data=json.dumps(payload), verify=False, timeout=10)
        
        logger.info(f"   응답 상태: {response.status_code}")
        
        # 401/403 인증 오류 시 재로그인 후 재시도
        if response.status_code in [401, 403] and retry_on_auth_fail:
            logger.info("   세션 만료 감지, 재로그인 후 재시도...")
            from util import load_yaml, merge_configs
            user_config = load_yaml('config.user.yaml')
            default_config = load_yaml('config.default.yaml')
            merged_config = merge_configs(default_config, user_config)
            
            if 로그인(merged_config):
                logger.info("   재로그인 성공")
                # 재귀 호출 (retry_on_auth_fail=False로 무한 루프 방지)
                return 예약조회요청(prvdDt, bizplcCd, retry_on_auth_fail=False)
            else:
                logger.error("   재로그인 실패")
                return []
        
        if response.status_code != 200:
            logger.warning(f"   예약 조회 오류: HTTP {response.status_code}")
            return []
        
        if len(response.text) == 0:
            logger.warning("   예약 조회 응답이 비어있음")
            return []
            
    except Exception as e:
        logger.error(f"   예약 조회 요청 실패: {e}")
        return []
    
    try:
        result = response.json()
    except Exception as e:
        logger.error(f"   JSON 파싱 실패: {e}")
        return []
    
    if result.get('errorCode') == 0:
        datasets = result.get('dataSets', {})
        reservations = datasets.get('reserveList', [])
        
        logger.info(f"   응답 예약 건수: {len(reservations)}건")
        
        # 모든 예약 항목의 prvdDt와 conerNm 로깅
        if reservations:
            logger.info("   응답 예약 목록:")
            for idx, res in enumerate(reservations, 1):
                prvd_dt = res.get('prvdDt', '')
                coner_nm = res.get('conerNm', '')
                disp_nm = res.get('dispNm', '')
                rsv_stat_cd = res.get('rsvStatCd', '')
                logger.info(f"      [{idx}] prvdDt={prvd_dt}, conerNm={coner_nm}, dispNm={disp_nm}, rsvStatCd={rsv_stat_cd}")
        
        # 모든 예약 반환 (필터링하지 않음)
        return reservations
    else:
        error_code = result.get('errorCode')
        error_msg = result.get('errorMsg', '')
        logger.warning(f"   API 오류: errorCode={error_code}, errorMsg={error_msg}")
    
    return []


def show_current_reservations(prvdDt):
    """현재 예약 현황 출력 (여러 날짜 가능)"""
    logger.info("\n" + "="*60)
    logger.info("📋 기존 예약 내역 조회")
    logger.info("="*60)
    
    reservations = 예약조회요청(prvdDt)
    
    if reservations:
        # rsvStatCd가 'A'인 예약만 필터링 (예약 완료 상태)
        confirmed = [r for r in reservations if r.get('rsvStatCd') == 'A']
        
        if confirmed:
            # prvdDt별로 그룹화
            from collections import defaultdict
            by_date = defaultdict(list)
            for res in confirmed:
                date = res.get('prvdDt', '')
                by_date[date].append(res)
            
            # 날짜 순으로 정렬하여 표시
            for date in sorted(by_date.keys()):
                # 날짜 포맷팅 (YYYYMMDD -> YYYY-MM-DD)
                if len(date) == 8:
                    formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
                else:
                    formatted_date = date
                
                logger.info(f"✅ {formatted_date} 예약 완료:")
                for res in by_date[date]:
                    coner_nm = res.get('conerNm', '알 수 없음')
                    disp_nm = res.get('dispNm', '')
                    if disp_nm:
                        logger.info(f"   • {coner_nm} - {disp_nm}")
                    else:
                        logger.info(f"   • {coner_nm}")
        else:
            # 날짜 포맷팅
            if len(prvdDt) == 8:
                formatted_date = f"{prvdDt[:4]}-{prvdDt[4:6]}-{prvdDt[6:]}"
            else:
                formatted_date = prvdDt
            logger.info(f"📌 {formatted_date}: 예약 없음 → 예약 대기 중")
    else:
        # 날짜 포맷팅
        if len(prvdDt) == 8:
            formatted_date = f"{prvdDt[:4]}-{prvdDt[4:6]}-{prvdDt[6:]}"
        else:
            formatted_date = prvdDt
        logger.info(f"📌 {formatted_date}: 예약 없음 → 예약 대기 중")
    
    logger.info("="*60 + "\n")


def 예약취소요청(reservation_data):
    """예약 취소 요청 - 예약 데이터 전체를 받아서 취소"""
    url = "https://hcafe.hgreenfood.com/api/menu/reservation/updateMenuReservationCancel.do"
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://hcafe.hgreenfood.com/ctf/menu/reservation/menuReservation.do",
        "Origin": "https://hcafe.hgreenfood.com"
    }

    # 예약 데이터를 그대로 사용
    payload = reservation_data
    
    prvd_dt = reservation_data.get('prvdDt', '')
    coner_nm = reservation_data.get('conerNm', '')
    
    logger.info(f"🌐 API 호출: updateMenuReservationCancel.do")
    logger.info(f"   요청 파라미터: prvdDt={prvd_dt}, conerNm={coner_nm}")

    response = session.post(url, headers=headers, data=json.dumps(payload), verify=False, timeout=10)

    logger.info(f"   응답 상태: {response.status_code}")
    
    try:
        resp_json = response.json()
        error_code = resp_json.get('errorCode')
        error_msg = resp_json.get('errorMsg')
        logger.info(f"   응답 내용: errorCode={error_code}, errorMsg={error_msg}")
        
        # errorCode가 0이면 성공
        return response.status_code == 200 and error_code == 0
    except Exception as e:
        logger.warning(f"   응답 본문 (JSON 파싱 실패): {response.text[:500]}")
        return False


menu_corner_map = {
    "샌": "0005",
    "샐": "0006",
    "빵": "0007",
    "헬": "0009",
    "닭": "0010"
}


def reserve(merged_config, prvdDt, login_once=True):
    """
    예약 시도 (기본값: 세션 재사용)
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

            # response.json() 호출을 try/except로 감싸서 JSONDecodeError 방지
            try:
                result_json = response.json()
                error_code = result_json.get('errorCode')
                error_msg = result_json.get('errorMsg', '알 수 없는 오류')
            except Exception as e:
                logger.error(f"❌ 예약 응답 JSON 파싱 실패: {e}")
                error_code = -1
                error_msg = f"JSON 파싱 실패: {str(e)}"

            log_entry = {
                "date": prvdDt,
                "requested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "menu": conerDvCd,
                "menu_name": menuInitial,
                "status_code": response.status_code,
                "errorCode": error_code,
                "errorMsg": error_msg
            }

            # 401/403 인증 오류 처리
            if response.status_code in [401, 403]:
                logger.warning(f"⚠️ 인증 오류 ({response.status_code}) - 재로그인 시도")
                if 로그인(merged_config, force=True):
                    logger.info("재로그인 성공 - 예약 재시도")
                    # 재로그인 후 같은 메뉴로 재시도
                    response = 예약주문요청(merged_config, conerDvCd, prvdDt)
                    try:
                        result_json = response.json()
                        error_code = result_json.get('errorCode')
                        error_msg = result_json.get('errorMsg', '알 수 없는 오류')
                    except Exception as e:
                        logger.error(f"❌ 예약 응답 JSON 파싱 실패: {e}")
                        error_code = -1
                        error_msg = f"JSON 파싱 실패: {str(e)}"
                else:
                    logger.error("재로그인 실패")
                    reason = "재로그인 실패"
                    return False, reason
            
            if response.status_code == 200 and error_code == 0:
                logger.info(f"✅ {prvdDt} 에 {menuInitial} 예약 성공!")
                reserveOK = True
                reason = f"{menuInitial} 예약 성공"
                log_entry.update({"reserveOk": True})
                reserve_his_tbl.insert(log_entry)
                
                # 예약 성공 후 현재 예약 목록 출력
                show_current_reservations(prvdDt)
                break
            elif error_msg == '동일날짜에 이미 등록된 예약이 존재합니다.':
                logger.info(f"ℹ️ {prvdDt} 에 이미 다른 메뉴가 예약되어 있음")
                reserveOK = True
                reason = "이미 예약됨"
                log_entry.update({"reserveOk": True})
                reserve_his_tbl.insert(log_entry)
                
                # 이미 예약된 경우에도 현재 예약 목록 출력
                show_current_reservations(prvdDt)
                break
            else:
                # 해당 메뉴 실패 - 다음 메뉴 시도
                logger.warning(f"⚠️ {menuInitial} 예약 실패: {error_msg}")
                log_entry.update({"reserveOk": False})
                reserve_his_tbl.insert(log_entry)
                reason = f"모든 메뉴 실패"

    return reserveOK, reason


def process_missed_reservations(merged_config):
    """
    놓친 예약이 있는지 확인하고 처리합니다.
    예: 토요일에 프로그램을 켰는데, 다음주 월요일 예약이 안되어 있다면 (금요일 13시에 했어야 함)
    지금이라도 예약을 시도합니다.
    """
    logger.info("🔍 놓친 예약 확인 중...")
    
    holiday = Holiday(merged_config)
    
    # 1. 현재 시점에서 가장 가까운 '미래의 근무일' (Target Date) 찾기
    # 오늘이 근무일이면 오늘 포함, 아니면 다음 근무일
    # 예: 토요일 -> 월요일
    # 예: 월요일 -> 월요일
    nearest_workday = holiday.get_nearest_future_workday()
    
    # 2. 그 근무일을 예약하기 위한 'Action Date' (이전 근무일) 찾기
    # 예: 월요일의 Action Date -> 금요일
    action_date_str = holiday.get_previous_workday(nearest_workday)
    
    # 3. Action Date의 13:00가 지났는지 확인
    action_dt = datetime.strptime(action_date_str, '%Y%m%d')
    action_deadline = action_dt.replace(
        hour=merged_config["reserve"]["at"]["hour"],
        minute=merged_config["reserve"]["at"]["minute"],
        second=merged_config["reserve"]["at"]["second"],
        microsecond=0
    )
    
    now = datetime.now()
    
    # 만약 지금이 Action Deadline보다 늦었다면 -> 이미 예약이 되어 있어야 함
    if now > action_deadline:
        logger.info(f"   확인 대상: {nearest_workday} (예약 실행일: {action_date_str} 13:00 지남)")
        
        # 예약 상태 확인
        reservations = 예약조회요청(nearest_workday)
        is_reserved = False
        
        if reservations:
            confirmed = [r for r in reservations if r.get('prvdDt') == nearest_workday and r.get('rsvStatCd') == 'A']
            if confirmed:
                # Regular menu codes (Sandwich, Salad, Bakery, Healthy, Chicken)
                REGULAR_MENU_CODES = ["0005", "0006", "0007", "0009", "0010"]
                
                # Check if any existing reservation is a "Regular Menu"
                has_regular = any(r.get('conerDvCd') in REGULAR_MENU_CODES for r in confirmed)
                
                if has_regular:
                    is_reserved = True
                    menus = [r.get('conerNm', '알 수 없음') for r in confirmed]
                    logger.info(f"   ✅ {nearest_workday} 이미 예약됨: {', '.join(menus)}")
                else:
                    # Only special menus are reserved -> Proceed to reserve regular menu
                    is_reserved = False
                    menus = [r.get('conerNm', '알 수 없음') for r in confirmed]
                    logger.info(f"   ℹ️ {nearest_workday} 특별 메뉴만 예약됨({', '.join(menus)}). 일반 메뉴 예약 시도...")
        
        if not is_reserved:
            logger.warning(f"   ⚠️ {nearest_workday} 예약이 누락되었습니다! 즉시 예약 시도합니다.")
            
            # 휴가 여부 확인
            db = TinyDB(DB_FILE, ensure_ascii=False, encoding='utf-8')
            vacation_tbl = db.table(VACATION_TBL_NM)
            vacation_dates = vacation_tbl.search(Query().date == nearest_workday)
            
            if vacation_dates:
                reason = vacation_dates[0].get('reason', '휴가')
                logger.info(f"   🏖️ {nearest_workday}는 휴가({reason})입니다. 예약 건너뜀")
                return

            # 강제 로그인 및 예약 시도
            if not 로그인(merged_config, force=True):
                logger.error("   ❌ 긴급 예약 시도 중 로그인 실패")
                return
                
            max_retries = 3
            retry_count = 0
            success = False
            
            while retry_count < max_retries:
                retry_count += 1
                logger.info(f"   🔄 긴급 예약 시도 {retry_count}/{max_retries}")
                
                result, reason = reserve(merged_config, nearest_workday, login_once=True)
                
                if result:
                    logger.info(f"   ✅ {nearest_workday} 긴급 예약 성공: {reason}")
                    success = True
                    break
                else:
                    logger.warning(f"   ⚠️ 긴급 예약 실패: {reason}")
                    time.sleep(2)
            
            if not success:
                logger.error(f"   ❌ {nearest_workday} 긴급 예약 최종 실패")
    else:
        logger.info(f"   다음 예약 대상: {nearest_workday} (아직 예약 시간 전임)")



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

        # Windows Credential Manager에서 마스터 패스워드 조회 시도
        try:
            import keyring
            saved_password = keyring.get_password("hgreenfood-auto-salad", "master_password")
            if saved_password:
                print("🔐 Windows 자격 증명 관리자에서 마스터 패스워드를 찾았습니다.")
                from setup_config import load_and_decrypt_config
                decrypted_config = load_and_decrypt_config(saved_password)
                
                if decrypted_config:
                    print("✅ 설정 파일 로드 완료 (자동 로그인)\n")
                    return decrypted_config
                else:
                    print("⚠️ 저장된 패스워드가 올바르지 않습니다. 다시 입력해주세요.")
        except Exception as e:
            logger.debug(f"Credential Manager 조회 실패: {e}")

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            master_password = getpass.getpass(f"마스터 패스워드를 입력하세요 ({attempt}/{max_attempts}): ")
            
            from setup_config import load_and_decrypt_config
            decrypted_config = load_and_decrypt_config(master_password)
            
            if decrypted_config:
                print("✅ 설정 파일 로드 완료\n")
                
                # 성공한 패스워드를 Credential Manager에 자동 저장
                try:
                    import keyring
                    keyring.set_password("hgreenfood-auto-salad", "master_password", master_password)
                    print("💾 마스터 패스워드가 Windows 자격 증명 관리자에 자동 저장되었습니다.")
                    print("   (다음 실행부터는 입력하지 않아도 됩니다)")
                except Exception as e:
                    logger.debug(f"Credential Manager 저장 실패: {e}")
                
                return decrypted_config
            else:
                if attempt < max_attempts:
                    print(f"❌ 마스터 패스워드가 올바르지 않습니다. (남은 시도: {max_attempts - attempt}회)")
                else:
                    logger.error("❌ 마스터 패스워드 입력 실패 횟수 초과. 프로그램을 종료합니다.")
                    sys.exit(1)
    
    # 구 버전 (암호화되지 않은 설정)
    return user_config


def console_menu_thread():
    """대기 중 사용자 입력을 받는 콘솔 메뉴 스레드"""
    import time
    
    # 메인 스레드의 로그가 완료될 때까지 잠시 대기
    time.sleep(0.5)
    
    # 최초 1회 메뉴 표시
    print("\n" + "="*60)
    print("📋 대기 중 메뉴 (언제든 명령 입력 가능)")
    print("="*60)
    print("1. 휴가 날짜 추가")
    print("2. 휴가 날짜 목록 보기")
    print("3. 휴가 날짜 삭제")
    print("4. 예약 목록 보기")
    print("5. 예약 취소")
    print("0/q. 종료")
    print("="*60)
    print()  # 빈 줄 추가
    
    while True:
        try:
            choice = input("선택: ").strip()
            
            if choice == "0" or choice.lower() == "q":
                logger.info("사용자가 종료를 요청했습니다.")
                os._exit(0)
            elif choice == "1":
                add_vacation_date()
            elif choice == "2":
                show_vacation_dates()
            elif choice == "3":
                delete_vacation_date()
            elif choice == "4":
                show_upcoming_reservations()
            elif choice == "5":
                cancel_reservation_interactive()
            elif choice == "":
                # Enter만 누르면 메뉴 다시 표시
                print("\n" + "="*60)
                print("📋 대기 중 메뉴")
                print("="*60)
                print("1. 휴가 날짜 추가")
                print("2. 휴가 날짜 목록 보기")
                print("3. 휴가 날짜 삭제")
                print("4. 예약 목록 보기")
                print("5. 예약 취소")
                print("0/q. 종료")
                print("="*60)
            else:
                print("❌ 잘못된 선택입니다. (1-5, 0/q 중 선택)")
        except KeyboardInterrupt:
            print("\n")
            logger.info("사용자가 프로그램을 중단했습니다. (Ctrl+C)")
            os._exit(0)
        except EOFError:
            print("\n")
            logger.info("사용자가 프로그램을 중단했습니다. (EOF)")
            os._exit(0)
        except Exception as e:
            logger.error(f"콘솔 메뉴 오류: {e}")
            import traceback
            logger.debug(traceback.format_exc())

def add_vacation_date():
    """휴가 날짜 추가"""
    try:
        date = input("휴가 날짜 (YYYYMMDD, Enter=취소): ").strip()
        
        if not date:
            print("취소되었습니다.")
            return
        
        if len(date) != 8 or not date.isdigit():
            print("❌ 날짜 형식이 올바르지 않습니다. (예: 20251225)")
            return
        
        reason = input("사유 (선택, Enter=휴가): ").strip() or "휴가"
        
        db = TinyDB(DB_FILE, ensure_ascii=False, encoding='utf-8')
        vacation_tbl = db.table(VACATION_TBL_NM)
        
        existing = vacation_tbl.search(Query().date == date)
        if existing:
            formatted = f"{date[:4]}-{date[4:6]}-{date[6:]}"
            print(f"⚠️ {formatted}는 이미 등록되어 있습니다.")
            return
        
        vacation_tbl.insert({"date": date, "reason": reason})
        formatted = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        print(f"✅ {formatted} ({reason}) 추가되었습니다.")
        
        # 대기 중단 신호
        wait_interrupt_event.set()
    except Exception as e:
        print(f"❌ 휴가 추가 중 오류: {e}")
        logger.error(f"휴가 추가 오류: {e}")

def clean_old_vacation_dates():
    """오늘 이전의 휴가 날짜 자동 삭제"""
    try:
        db = TinyDB(DB_FILE, ensure_ascii=False, encoding='utf-8')
        vacation_tbl = db.table(VACATION_TBL_NM)
        
        today = datetime.now().strftime('%Y%m%d')
        
        # 오늘 이전 날짜 찾기
        old_vacations = [v for v in vacation_tbl.all() if v.get('date', '99999999') < today]
        
        if old_vacations:
            # 삭제
            for v in old_vacations:
                vacation_tbl.remove(Query().date == v['date'])
            
            logger.info(f"🗑️ 과거 휴가 날짜 {len(old_vacations)}건 자동 삭제")
            return len(old_vacations)
        
        return 0
    except Exception as e:
        logger.error(f"과거 휴가 날짜 삭제 오류: {e}")
        return 0

def show_vacation_dates():
    """휴가 날짜 목록 보기 (오늘 이후만)"""
    try:
        db = TinyDB(DB_FILE, ensure_ascii=False, encoding='utf-8')
        vacation_tbl = db.table(VACATION_TBL_NM)
        
        # 오늘 날짜
        today = datetime.now().strftime('%Y%m%d')
        
        # 오늘 이후 날짜만 필터링
        vacations = [v for v in vacation_tbl.all() if v.get('date', '99999999') >= today]
        
        if not vacations:
            print("\n📅 등록된 휴가 날짜가 없습니다.")
            return
        
        # date 필드로 정렬
        sorted_vacations = sorted(vacations, key=lambda x: x.get('date', '99999999'))
        
        print("\n📅 등록된 휴가 날짜 (오늘 이후):")
        for v in sorted_vacations:
            date = v.get('date', '알 수 없음')
            reason = v.get('reason', '휴가')
            
            # 날짜 포맷팅 (YYYYMMDD -> YYYY-MM-DD)
            if len(date) == 8 and date.isdigit():
                formatted = f"{date[:4]}-{date[4:6]}-{date[6:]}"
            else:
                formatted = date
            
            print(f"   {formatted}: {reason}")
        
        print(f"\n   총 {len(sorted_vacations)}개의 휴가 날짜가 등록되어 있습니다.")
    except Exception as e:
        print(f"❌ 휴가 목록 조회 중 오류: {e}")
        logger.error(f"휴가 목록 조회 오류: {e}")

def delete_vacation_date():
    """휴가 날짜 삭제"""
    try:
        db = TinyDB(DB_FILE, ensure_ascii=False, encoding='utf-8')
        vacation_tbl = db.table(VACATION_TBL_NM)
        
        # 먼저 목록 표시
        vacations = vacation_tbl.all()
        if not vacations:
            print("\n📅 등록된 휴가 날짜가 없습니다.")
            return
        
        print("\n📅 현재 등록된 휴가 날짜:")
        sorted_vacations = sorted(vacations, key=lambda x: x.get('date', '99999999'))
        for v in sorted_vacations:
            date = v.get('date', '')
            reason = v.get('reason', '휴가')
            if len(date) == 8 and date.isdigit():
                formatted = f"{date[:4]}-{date[4:6]}-{date[6:]}"
            else:
                formatted = date
            print(f"   {formatted}: {reason}")
        
        print()
        date = input("삭제할 휴가 날짜 (YYYYMMDD, Enter=취소): ").strip()
        
        if not date:
            print("취소되었습니다.")
            return
        
        removed = vacation_tbl.remove(Query().date == date)
        if removed:
            print(f"✅ {date} 삭제되었습니다.")
            # 대기 중단 신호
            wait_interrupt_event.set()
        else:
            print(f"❌ {date}를 찾을 수 없습니다.")
    except Exception as e:
        print(f"❌ 휴가 삭제 중 오류: {e}")
        logger.error(f"휴가 삭제 오류: {e}")

def show_upcoming_reservations():
    """예약 목록을 조회하여 표시 (전체 조회)"""
    print("\n" + "="*60)
    print("📋 예약 목록 조회 중...")
    print("="*60)
    
    today = datetime.now().strftime('%Y%m%d')
    
    # 오늘 날짜로 한 번만 조회하면 전체 목록이 반환됨
    reservations = 예약조회요청(today, retry_on_auth_fail=True)
    
    if not reservations:
        print("\n📌 조회된 예약 내역이 없습니다.")
        print("="*60 + "\n")
        return

    # rsvStatCd가 'A'인 예약만 필터링
    confirmed = [r for r in reservations if r.get('rsvStatCd') == 'A']
    
    if not confirmed:
        print("\n📌 예약된 내역이 없습니다.")
        print("="*60 + "\n")
        return
    
    # 날짜별로 그룹화
    from collections import defaultdict
    by_date = defaultdict(list)
    
    for res in confirmed:
        prvd_dt = res.get('prvdDt', '')
        if prvd_dt:
            by_date[prvd_dt].append(res)
    
    # 날짜 순으로 정렬하여 표시
    for date in sorted(by_date.keys()):
        # 날짜 포맷팅
        if len(date) == 8:
            formatted = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        else:
            formatted = date
            
        menus = []
        for r in by_date[date]:
            menu = r.get('conerNm', '알 수 없음')
            disp = r.get('dispNm', '')
            if disp:
                menus.append(f"{menu}({disp})")
            else:
                menus.append(menu)
        
        print(f"✅ {formatted}: {', '.join(menus)}")
    
    print("="*60 + "\n")


def show_reservations_interactive():
    """현재 예약 조회 (대화형)"""
    date = input("조회할 날짜 (YYYYMMDD, Enter=내일): ").strip()
    
    if not date:
        from holiday import Holiday
        from util import load_yaml, merge_configs
        user_config = load_yaml('config.user.yaml')
        default_config = load_yaml('config.default.yaml')
        merged_config = merge_configs(default_config, user_config)
        holiday = Holiday(merged_config)
        date = holiday.get_next_action_date()
        # 만약 action_date가 오늘이고 13시 이전이면, 사용자가 조회를 원하는건 아마도 '오늘 예약'이거나 '내일 예약'일 것임.
        # 하지만 여기서는 '다음 예약 대상일'을 보여주는게 맞음.
        # get_next_action_date가 오늘을 리턴하면 -> target은 내일
        target_date = holiday.get_target_service_date(date)
        date = target_date
    
    if len(date) != 8 or not date.isdigit():
        print("❌ 날짜 형식이 올바르지 않습니다.")
        return
    
    reservations = 예약조회요청(date)
    formatted = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    
    if reservations:
        print(f"\n📋 {formatted} 예약 내역:")
        for res in reservations:
            menu = res.get('conerNm', '알 수 없음')
            print(f"   ✅ {menu}")
    else:
        print(f"\n📋 {formatted}: 예약 없음")

def cancel_reservation_interactive():
    """예약 취소 (대화형) - 현재 예약 목록에서만 선택"""
    
    # 오늘부터 일주일치 예약 조회 (여러 날짜 예약이 함께 반환됨)
    from datetime import timedelta
    today = datetime.now().strftime('%Y%m%d')
    reservations = 예약조회요청(today)
    
    if not reservations:
        print("\n📋 취소 가능한 예약이 없습니다.")
        return
    
    # 예약된 항목 중 rsvStatCd가 'A'인 것만 필터링하고 날짜별로 그룹화
    from collections import defaultdict
    by_date = defaultdict(list)
    
    for res in reservations:
        if res.get('rsvStatCd') == 'A':
            prvd_dt = res.get('prvdDt', '')
            if prvd_dt:
                by_date[prvd_dt].append(res)
    
    if not by_date:
        print("\n📋 취소 가능한 예약이 없습니다.")
        return
    
    # 예약 목록을 번호와 함께 표시
    print("\n" + "="*60)
    print("📋 취소 가능한 예약 목록")
    print("="*60)
    
    all_reservations = []
    idx = 1
    
    for date in sorted(by_date.keys()):
        # 날짜 포맷팅
        formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        print(f"\n📅 {formatted_date}:")
        
        for res in by_date[date]:
            coner_nm = res.get('conerNm', '알 수 없음')
            disp_nm = res.get('dispNm', '')
            if disp_nm:
                print(f"   {idx}. {coner_nm} - {disp_nm}")
            else:
                print(f"   {idx}. {coner_nm}")
            
            all_reservations.append(res)
            idx += 1
    
    print("="*60)
    
    # 취소할 예약 선택
    choice = input(f"\n취소할 예약 번호 (1-{len(all_reservations)}, Enter=이전 단계로): ").strip()
    
    if not choice:
        print("이전 단계로 돌아갑니다.")
        return
    
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(all_reservations):
            print("❌ 잘못된 번호입니다.")
            return
        
        selected = all_reservations[idx]
        
        # 예약 취소 요청
        result = 예약취소요청(selected)
        
        if result:
            prvd_dt = selected.get('prvdDt', '')
            coner_nm = selected.get('conerNm', '알 수 없음')
            formatted_date = f"{prvd_dt[:4]}-{prvd_dt[4:6]}-{prvd_dt[6:]}" if len(prvd_dt) == 8 else prvd_dt
            print(f"\n✅ {formatted_date} {coner_nm} 예약이 취소되었습니다.")
            
            # 취소 후 현재 예약 목록 출력
            show_current_reservations(today)
        else:
            print(f"\n❌ 예약 취소에 실패했습니다.")
            
    except ValueError:
        print("❌ 숫자를 입력해주세요.")
    except Exception as e:
        print(f"❌ 예약 취소 중 오류: {e}")
        logger.error(f"예약 취소 오류: {e}")


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
        
        # 과거 휴가 날짜 정리
        cleaned_count = clean_old_vacation_dates()
        if cleaned_count > 0:
            logger.info(f"🗑️ 과거 휴가 날짜 {cleaned_count}건 자동 삭제 완료")
        
        # 항상 새로 로그인 (기존 쿠키 사용 안 함)
        if not 로그인(merged_config, force=True):
            logger.error("초기 로그인 실패. 프로그램 종료")
            return
        
        # 놓친 예약 확인 및 처리
        process_missed_reservations(merged_config)
        
        # 콘솔 메뉴 스레드 시작 (데몬 스레드로 백그라운드 실행)
        console_thread = threading.Thread(target=console_menu_thread, daemon=True)
        console_thread.start()

        while True:
            now = datetime.now()
            today = now.strftime('%Y%m%d')
            
            # 휴일 캐시 업데이트 (매월 1일에)
            if now.day == 1:
                holiday.update_holidays_cache(now.year, now.month)
            
            cached_holidays = holiday.get_cached_holidays(now.year, now.month)[0]
            
            # 다음 예약 실행 날짜(Action Date) 계산
            # 예: 월 09:00 -> 월 13:00 (오늘)
            # 예: 월 14:00 -> 화 13:00 (내일)
            action_date_str = holiday.get_next_action_date()
            
            # 예약 대상 식단 날짜(Service Date) 계산
            # 예: Action(월) -> Service(화)
            target_service_date = holiday.get_target_service_date(action_date_str)
            
            logger.info(f"현재: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"📅 다음 동작 예정일(Action): {action_date_str} 13:00")
            logger.info(f"🍱 예약 대상 식단일(Target): {target_service_date}")

            # DB 연결
            db = TinyDB(DB_FILE, ensure_ascii=False, encoding='utf-8')
            reserve_his_tbl = db.table(RESERVATION_HISTORY_TBL_NM)
            vacation_tbl = db.table(VACATION_TBL_NM)
            
            # 휴가 날짜 확인 (예약 대상 날짜가 휴가인지)
            vacation_dates = vacation_tbl.search(Query().date == target_service_date)
            if vacation_dates:
                vacation = vacation_dates[0]
                reason = vacation.get('reason', '휴가')
                logger.info(f"🏖️ {target_service_date}는 예약 금지 날짜입니다 ({reason}).")
                # 휴가인 경우, 그냥 다음 턴으로 넘어가야 함.
                # 하지만 여기서 continue하면 바로 다시 루프가 돌아서 같은 날짜를 계산함.
                # 따라서 '다음 Action Date'까지 대기해야 함.
                
                # 현재 Action Date가 오늘이면 -> 내일 Action Date까지 대기
                # 현재 Action Date가 미래이면 -> 그 날짜까지 대기
                
                # 간단히 처리하기 위해 sleep_until_next_action 호출
                sleep_until_action_time(action_date_str, merged_config)
                
                # 깨어난 후 다시 루프 돌면, 시간이 흘렀으므로 get_next_action_date가 다음 날짜를 가리킬 것임
                # 단, 13시가 지나야 다음 날짜가 됨.
                # 만약 13시 1분에 깨어나면 -> get_next_action_date는 내일을 가리킴. OK.
                continue
            
            # 이미 예약 완료 여부 확인
            already_reserved = reserve_his_tbl.search(
                (Query().date == target_service_date) & (Query().reserveOk == True)
            )
            
            if already_reserved:
                logger.info(f"✅ {target_service_date} 이미 예약 완료되어 있습니다.")
                sleep_until_action_time(action_date_str, merged_config)
                continue
            
            # 예약 실행 시간 설정 (Action Date의 13:00:00)
            action_dt = datetime.strptime(action_date_str, '%Y%m%d')
            reservation_time = action_dt.replace(
                hour=merged_config["reserve"]["at"]["hour"],
                minute=merged_config["reserve"]["at"]["minute"],
                second=merged_config["reserve"]["at"]["second"],
                microsecond=0
            )
            
            # 예약 시간 체크
            time_until_reservation = (reservation_time - now).total_seconds()
            
            if time_until_reservation > 60:
                # 예약 시간까지 1분 이상 남음 - 대기
                logger.info(f"⏳ 예약 시간({reservation_time})까지 대기 ({time_until_reservation/3600:.1f}시간)")
                # sleep_until_action_time 함수를 사용하여 대기 (인터럽트 지원)
                sleep_until_action_time(action_date_str, merged_config)
                continue
            
            elif -5 < time_until_reservation <= 60:
                # 예약 시간 5초 전부터 1분 후까지 - 예약 시도
                logger.info("⏰ 예약 시간 도달! 예약 시도 시작")
                
                # 13시 정각에는 반드시 강제 로그인 (세션 갱신)
                logger.info("🔐 예약 전 강제 로그인 수행...")
                if not 로그인(merged_config, force=True):
                    logger.error("❌ 예약 전 로그인 실패. 1분 후 재시도")
                    time.sleep(60)
                    continue

                max_retries = merged_config.get("max_retry", 10)
                retry_interval = merged_config.get("retry_interval", 5)
                
                retry_count = 0
                success = False
                
                while retry_count < max_retries:
                    retry_count += 1
                    logger.info(f"🔄 예약 시도 {retry_count}/{max_retries} (Target: {target_service_date})")
                    
                    # 예약 시도 (이미 로그인 했으므로 login_once=True)
                    result, reason = reserve(merged_config, target_service_date, login_once=True)
                    
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
                
                # 예약 시도 완료 후 잠시 대기 (중복 실행 방지)
                logger.info("💤 예약 시도 완료. 다음 사이클 대기...")
                time.sleep(120) 
            
            else:
                # 예약 시간이 1분 이상 지남 (이미 지났는데 예약 안된 경우)
                # 이 경우는 보통 프로그램이 13:01 이후에 켜진 경우인데,
                # get_next_action_date 로직상 13시 이후에 켜지면 '내일'을 가리키므로
                # 이 블록에 들어올 일은 거의 없음 (Action Date가 내일이면 time_until > 0 이므로)
                # 하지만 혹시 모르니 로그 남기고 대기
                logger.warning(f"⚠️ 예약 시간({reservation_time})이 지났습니다. 다음 사이클로 넘어갑니다.")
                time.sleep(60)

    except Exception as e:
        logger.error(f"에러 발생: {e}")
        logger.error(traceback.format_exc())  # 전체 Stack Trace 출력


# 대기 중단 이벤트 (휴가 추가/삭제 시 사용)
wait_interrupt_event = threading.Event()

def sleep_until_action_time(action_date_str, merged_config):
    """다음 Action Date의 13시까지 대기 (인터럽트 가능)"""
    action_dt = datetime.strptime(action_date_str, '%Y%m%d')
    target_time = action_dt.replace(
        hour=merged_config["reserve"]["at"]["hour"],
        minute=merged_config["reserve"]["at"]["minute"],
        second=merged_config["reserve"]["at"]["second"],
        microsecond=0
    )

    current_time = datetime.now()
    sleep_duration = (target_time - current_time).total_seconds()

    # 이미 지났으면 (예: 13:00:01에 호출됨) -> 그냥 리턴해서 루프 다시 돌게 함
    # 하지만 루프에서 다시 여기로 오면 무한루프 돌 수 있음.
    # 따라서 최소 10초 대기
    if sleep_duration <= 0:
        logger.debug(f"목표 시간({target_time})이 과거입니다. 잠시 대기 후 재확인")
        time.sleep(10)
        return

    logger.info(f"💤 대기 모드: {target_time.strftime('%Y-%m-%d %H:%M:%S')}까지 대기 ({sleep_duration/3600:.1f}시간)")
    
    # 인터럽트 가능한 대기 (1분 단위로 체크)
    elapsed = 0
    while elapsed < sleep_duration:
        # 1분마다 로그 찍으면 너무 많으니 1시간마다 찍거나 조용히 대기
        if wait_interrupt_event.wait(timeout=min(60, sleep_duration - elapsed)):
            logger.info("⚠️ 대기 중단 요청 감지. 즉시 재시작합니다.")
            wait_interrupt_event.clear()
            return
        elapsed += 60
        
        # 남은 시간 갱신 (정확도 위해)
        remaining = (target_time - datetime.now()).total_seconds()
        if remaining <= 0:
            break

if __name__ == '__main__':
    main()
