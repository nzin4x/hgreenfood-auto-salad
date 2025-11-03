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


def 로그인(merged_config, force=False):
    """로그인 수행 (force=True일 때만 강제 재로그인)"""
    # 이미 쿠키 파일이 있고 force가 아니면 기존 세션 사용
    import os
    if not force and os.path.exists('cookies.txt'):
        logger.debug("기존 로그인 세션 재사용")
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

    logger.info(f"🌐 API 호출: login.do")
    logger.info(f"   요청 파라미터: userId={merged_config['userId']}")

    response = session.post(url, headers=headers, data=json.dumps(payload), verify=False)

    logger.info(f"   응답 상태: {response.status_code}")

    if json.loads(response.content)['errorCode'] == 0:
        logger.info("   로그인 성공")
        save_cookies(response.cookies, 'cookies.txt')
        return True
    else:
        logger.error(f"   로그인 실패: errorCode={json.loads(response.content).get('errorCode')}")
        logger.error(f"   응답 내용: {response.text[:200]}")
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

    response = session.post(url, headers=headers, data=json.dumps(payload), verify=False, timeout=10)

    logger.info(f"취소 응답 코드: {response.status_code}")
    try:
        logger.debug(f"취소 응답 내용: {response.json()}")
    except:
        logger.debug(f"취소 응답 본문 (JSON 파싱 실패): {response.text[:500]}")

    return response


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

            if response.status_code == 200 and error_code == 0:
                logger.info(f"✅ {prvdDt} 에 {menuInitial} 예약 성공!")
                reserveOK = True
                reason = f"{menuInitial} 예약 성공"
                log_entry.update({"reserveOk": True})
                reserve_his_tbl.insert(log_entry)
                break
            elif error_msg == '동일날짜에 이미 등록된 예약이 존재합니다.':
                logger.info(f"ℹ️ {prvdDt} 에 이미 다른 메뉴가 예약되어 있음")
                reserveOK = True
                reason = "이미 예약됨"
                log_entry.update({"reserveOk": True})
                reserve_his_tbl.insert(log_entry)
                break
            else:
                # 해당 메뉴 실패 - 다음 메뉴 시도
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


def console_menu_thread():
    """대기 중 사용자 입력을 받는 콘솔 메뉴 스레드"""
    # 최초 1회 메뉴 표시
    print("\n" + "="*60)
    print("📋 대기 중 메뉴 (언제든 명령 입력 가능)")
    print("="*60)
    print("1. 휴가 날짜 추가")
    print("2. 휴가 날짜 목록 보기")
    print("3. 휴가 날짜 삭제")
    print("4. 현재 예약 조회")
    print("0. 종료")
    print("="*60)
    
    while True:
        try:
            choice = input("\n선택: ").strip()
            
            if choice == "0":
                logger.info("사용자가 종료를 요청했습니다.")
                os._exit(0)
            elif choice == "1":
                add_vacation_date()
            elif choice == "2":
                show_vacation_dates()
            elif choice == "3":
                delete_vacation_date()
            elif choice == "4":
                show_reservations_interactive()
            elif choice == "":
                # Enter만 누르면 메뉴 다시 표시
                print("\n" + "="*60)
                print("📋 대기 중 메뉴")
                print("="*60)
                print("1. 휴가 날짜 추가")
                print("2. 휴가 날짜 목록 보기")
                print("3. 휴가 날짜 삭제")
                print("4. 현재 예약 조회")
                print("0. 종료")
                print("="*60)
            else:
                print("❌ 잘못된 선택입니다. (1-4, 0 중 선택)")
        except KeyboardInterrupt:
            logger.info("\n사용자가 프로그램을 중단했습니다.")
            os._exit(0)
        except Exception as e:
            logger.error(f"콘솔 메뉴 오류: {e}")

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
        date = holiday.다음_근무일(datetime.now().strftime('%Y%m%d'))
    
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
        
        # 현재 예약 현황 조회 (오늘 기준으로 조회하면 여러 날짜 예약이 함께 반환됨)
        now = datetime.now()
        today = now.strftime('%Y%m%d')
        show_current_reservations(today)
        
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


# 대기 중단 이벤트 (휴가 추가/삭제 시 사용)
wait_interrupt_event = threading.Event()

def sleep_until_next_workday_noon(prvdDt, merged_config):
    """다음 예약 시간까지 대기 (인터럽트 가능)"""
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
    
    # 예약 상태 확인 (prvdDt에 해당하는 예약만 확인)
    reservations = 예약조회요청(prvdDt)
    if reservations:
        # prvdDt가 정확히 일치하고 rsvStatCd가 'A'인 예약만 필터링
        confirmed = [r for r in reservations if r.get('prvdDt') == prvdDt and r.get('rsvStatCd') == 'A']
        
        if confirmed:
            # 예약된 메뉴 목록
            menus = [r.get('conerNm', '알 수 없음') for r in confirmed]
            menu_str = ', '.join(menus)
            logger.info(f"✅ {formatted_date} 예약 완료: {menu_str}")
            logger.info(f"   → 다음 근무일 예약 대기")
        else:
            logger.info(f"📌 {formatted_date} 예약 예정 → 예약 시간 대기")
    else:
        logger.info(f"📌 {formatted_date} 예약 예정 → 예약 시간 대기")
    
    logger.info(f"⏰ 다음 예약 시간: {target_time.strftime('%Y-%m-%d %H:%M:%S')} ({sleep_duration/3600:.1f}시간 후)")
    
    # 인터럽트 가능한 대기 (1분 단위로 체크)
    elapsed = 0
    while elapsed < sleep_duration:
        if wait_interrupt_event.wait(timeout=min(60, sleep_duration - elapsed)):
            logger.info("⚠️ 대기 중단 요청 감지. 즉시 재시작합니다.")
            wait_interrupt_event.clear()
            return
        elapsed += 60

if __name__ == '__main__':
    main()
