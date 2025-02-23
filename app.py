# -*- coding: utf-8 -*-
import json
import logging
import time
import traceback
from datetime import datetime, timedelta

import requests
from tinydb import TinyDB

from config import DB_FILE, RESERVATION_HISTORY_TBL_NM
from holiday import Holiday
from util import load_yaml, merge_configs, already_done

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

def save_cookies(cookies, filename):
    with open(filename, 'w') as cookie_file:
        for cookie in cookies:
            cookie_file.write(f"{cookie.name}={cookie.value}\n")


def 로그인(merged_config):
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

    response = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)

    if json.loads(response.content)['errorCode'] == 0:
        print("로그인 성공")
        save_cookies(response.cookies, 'cookies.txt')
        return True
    else:
        print(f"로그인 실패: {response.status_code}, {response.text}")
        return False


def load_cookies(filename):
    cookies = {}
    with open(filename, 'r', encoding='utf-8') as cookie_file:
        for line in cookie_file:
            if line.strip():
                name, value = line.strip().split('=')
                cookies[name] = value
    return cookies


def 예약주문요청(config, conerDvCd, prvdDt):
    url = "https://hcafe.hgreenfood.com/api/menu/reservation/insertReservationOrder.do"
    headers = {
        "Content-Type": "application/json"
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

    cookies = load_cookies('cookies.txt')

    response = requests.post(url, headers=headers, data=json.dumps(payload), cookies=cookies, verify=False)

    print(f"응답 코드: {response.status_code}")
    print(f"응답 내용: {response.json()}")

    return response


menu_corner_map = {
    "샌": "0005",
    "샐": "0006",
    "빵": "0007",
    "닭": "0009"
}


def reserve(merged_config, prvdDt):
    if not 로그인(merged_config):
        return

    menuSeq = merged_config['menuSeq']
    menuInitials = [corner.strip() for corner in menuSeq.split(",")]

    db = TinyDB(DB_FILE, ensure_ascii=False, encoding='utf-8')
    reserve_his_tbl = db.table(RESERVATION_HISTORY_TBL_NM)

    reserveOK = False

    for menuInitial in menuInitials:
        conerDvCd = menu_corner_map.get(menuInitial.strip())

        if conerDvCd:
            response = 예약주문요청(merged_config, conerDvCd, prvdDt)

            log_entry = {
                "date": prvdDt,
                "requested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "menu": conerDvCd,
                "status_code": response.status_code,
                "errorCode": response.json().get('errorCode'),
                "errorMsg": response.json().get('errorMsg')
            }

            if response.status_code == 200 or already_done(response):
                print(f"{prvdDt} 에 {menuInitial} 예약 요청 성공: {response.json()}")
                reserveOK = True
                break
            else:
                reserveOK = False
                print(f"{prvdDt} 에 {menuInitial} 예약 요청 실패: {response.status_code}, {response.text}")

    log_entry.update({"reserveOk": reserveOK})
    reserve_his_tbl.insert(log_entry)

    return reserveOK


def main():
    try:
        default_config = load_yaml('config.default.yaml')
        user_config = load_yaml('config.user.yaml')

        merged_config = merge_configs(default_config, user_config)

        holiday = Holiday(merged_config)
        holiday.update_holidays_cache(datetime.today().year, datetime.today().month)

        cached_holidays = holiday.get_cached_holidays(datetime.today().year, datetime.today().month)[0]

        while True:
            today = datetime.today().strftime('%Y%m%d')
            prvdDt = holiday.다음_근무일(today)

            if today in cached_holidays or datetime.today().weekday() >= 5:
                sleep_until_next_workday_noon(prvdDt, merged_config)
            else:
                db = TinyDB(DB_FILE, ensure_ascii=False, encoding='utf-8')
                reserve_his_tbl = db.table(RESERVATION_HISTORY_TBL_NM)
                if reserve_his_tbl.search((lambda x: x['date'] == prvdDt and x['reserveOk'] == True)):
                    logger.info("이미 예약 완료된 날짜입니다.")
                else:
                    start_time = datetime.now().replace(
                        hour=merged_config["reserve"]["at"]["hour"],
                        minute=merged_config["reserve"]["at"]["minute"],
                        second=merged_config["reserve"]["at"]["second"],
                        microsecond=0
                    )
                    end_time = start_time + timedelta(seconds=merged_config["reserve"]["duration"]["seconds"])

                    while end_time > datetime.now() > start_time:
                        result = reserve(merged_config, prvdDt)

                        if result:
                            logger.info("예약 성공! 다음 근무일까지 sleep")
                            break

                        time.sleep(merged_config["reserve"]["duration"]["sleep_seconds"])

            logger.info("예약 가능 시간이 될 때까지 휴식 합니다.")
            sleep_until_next_workday_noon(prvdDt, merged_config)

    except Exception as e:
        logger.error(f"에러 발생: {e}")
        logger.error(traceback.format_exc())  # 전체 Stack Trace 출력


def sleep_until_next_workday_noon(prvdDt, merged_config):
    next_workday = datetime.strptime(prvdDt, '%Y%m%d')
    target_time = next_workday.replace(
        hour=merged_config["reserve"]["at"]["hour"],
        minute=merged_config["reserve"]["at"]["minute"],
        second=merged_config["reserve"]["at"]["second"],
        microsecond=0
    )

    current_time = datetime.now()
    sleep_duration = (target_time - current_time).total_seconds()

    logger.debug(f"DEBUG: current_time={current_time}, target_time={target_time}, sleep_duration={sleep_duration}")

    if sleep_duration <= 0:
        logger.warning(f"목표 시간이 과거입니다. 최소 1초 대기 후 실행됩니다.")
        sleep_duration = 1  # 최소 1초라도 대기

    logger.info(f"다음 근무일 예약시간 {target_time}까지 {sleep_duration}초 동안 대기합니다.")
    time.sleep(sleep_duration)

if __name__ == '__main__':
    main()
