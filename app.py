import json
import logging
import time
from datetime import datetime, timedelta

import requests
from tinydb import TinyDB

from holiday import Holiday
from util import load_yaml, merge_configs, already_done


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

    DB_FILE = "data.json"
    db = TinyDB(DB_FILE)
    ReservationHistory = db.table('ReservationHistory')

    reserveOK = False

    for menuInitial in menuInitials:
        conerDvCd = menu_corner_map.get(menuInitial.strip())

        if conerDvCd:
            response = 예약주문요청(merged_config, conerDvCd, prvdDt)

            log_entry = {
                "date": prvdDt,
                "menu": conerDvCd,
                "status_code": response.status_code,
                "response": json.dumps(response.json(), ensure_ascii=False)
            }

            if response.status_code == 200 or already_done(response):
                print(f"{prvdDt} 에 {menuInitial} 예약 요청 성공: {response.json()}")
                reserveOK = True
                break
            else:
                reserveOK = False
                print(f"{prvdDt} 에 {menuInitial} 예약 요청 실패: {response.status_code}, {response.text}")

    log_entry.update({"reserveOk": reserveOK})
    ReservationHistory.insert(log_entry)


logging.basicConfig(level=logging.INFO)


def main():
    try:
        default_config = load_yaml('config.default.yaml')
        user_config = load_yaml('config.user.yaml')

        merged_config = merge_configs(default_config, user_config)

        holiday = Holiday(merged_config)
        holiday.update_holidays_cache(datetime.today().year, datetime.today().month)

        cached_holidays = holiday.get_cached_holidays(datetime.today().year, datetime.today().month)[0]
        today = datetime.today().strftime('%Y%m%d')
        prvdDt = holiday.다음_근무일(today)

        while True:
            if today in cached_holidays or datetime.today().weekday() >= 5:
                sleep_until_next_workday_noon(prvdDt, merged_config)
            else:
                DB_FILE = "data.json"
                db = TinyDB(DB_FILE)
                ReservationHistory = db.table('ReservationHistory')
                if ReservationHistory.search((lambda x: x['date'] == prvdDt and x['reserveOk'] == True)):
                    logging.info("이미 예약 완료된 날짜입니다.")
                else:
                    start_time = datetime.now().replace(
                        hour=merged_config["reserve"]["at"]["hour"],
                        minute=merged_config["reserve"]["at"]["minute"],
                        second=merged_config["reserve"]["at"]["second"],
                        microsecond=0
                    )
                    end_time = start_time + timedelta(seconds=merged_config["reserve"]["duration"]["seconds"])

                    while end_time > datetime.now() > start_time:
                        reserve(merged_config, prvdDt)
                        time.sleep(merged_config["reserve"]["duration"]["sleep_seconds"])

            time.sleep(5)

    except Exception as e:
        logging.error(f"에러 발생: {e}")


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

    if sleep_duration <= 0:
        logging.warning(f"목표 시간이 과거입니다. 즉시 실행됩니다.")
        return 0

    logging.info(f"다음 근무일 예약시간 {target_time}까지 {sleep_duration}초 동안 대기합니다.")
    time.sleep(sleep_duration)


if __name__ == '__main__':
    main()
