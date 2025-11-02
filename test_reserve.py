# -*- coding: utf-8 -*-
"""
예약 및 취소 테스트 스크립트
"""
import json
import sys
from datetime import datetime

import requests

from config import DB_FILE, RESERVATION_HISTORY_TBL_NM
from holiday import Holiday
from util import load_yaml, merge_configs

# 전역 세션 객체
session = requests.Session()

def 로그인(merged_config):
    """로그인"""
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
        print("✅ 로그인 성공")
        return True
    else:
        print(f"❌ 로그인 실패: {response.status_code}, {response.text}")
        return False


def 예약주문요청(config, conerDvCd, prvdDt):
    """예약 주문"""
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

    print(f"📤 예약 응답 코드: {response.status_code}")
    print(f"📄 예약 응답 내용: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

    return response


def 예약취소요청(prvdDt):
    """예약 취소"""
    url = "https://hcafe.hgreenfood.com/api/menu/reservation/updateMenuReservationCancel.do"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }

    payload = {
        "prvdDt": prvdDt,
        "reseOrderDate": prvdDt
    }

    response = session.post(url, headers=headers, data=json.dumps(payload), verify=False)

    print(f"📤 취소 응답 코드: {response.status_code}")
    print(f"📄 취소 응답 내용: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

    return response


menu_corner_map = {
    "샌": "0005",
    "샐": "0006",
    "빵": "0007",
    "닭": "0009"
}


def test_reserve(merged_config, prvdDt):
    """예약 테스트"""
    print(f"\n{'='*60}")
    print(f"🎯 예약 테스트: {prvdDt}")
    print(f"{'='*60}\n")

    if not 로그인(merged_config):
        return False

    menuSeq = merged_config['menuSeq']
    menuInitials = [corner.strip() for corner in menuSeq.split(",")]

    for menuInitial in menuInitials:
        conerDvCd = menu_corner_map.get(menuInitial.strip())

        if conerDvCd:
            print(f"\n🍴 {menuInitial} (코드: {conerDvCd}) 예약 시도...")
            response = 예약주문요청(merged_config, conerDvCd, prvdDt)

            if response.status_code == 200 and response.json().get('errorCode') == 0:
                print(f"✅ {menuInitial} 예약 성공!")
                return True
            elif response.json().get('errorMsg') == '동일날짜에 이미 등록된 예약이 존재합니다.':
                print(f"ℹ️ {menuInitial} 이미 예약되어 있음")
                return True
            else:
                print(f"⚠️ {menuInitial} 예약 실패: {response.json().get('errorMsg')}")

    return False


def test_cancel(merged_config, prvdDt):
    """취소 테스트"""
    print(f"\n{'='*60}")
    print(f"🗑️ 취소 테스트: {prvdDt}")
    print(f"{'='*60}\n")

    if not 로그인(merged_config):
        return False

    response = 예약취소요청(prvdDt)

    if response.status_code == 200 and response.json().get('errorCode') == 0:
        print(f"✅ 취소 성공!")
        return True
    else:
        print(f"❌ 취소 실패: {response.json().get('errorMsg')}")
        return False


def main():
    # 경고 무시
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    default_config = load_yaml('config.default.yaml')
    user_config = load_yaml('config.user.yaml')
    merged_config = merge_configs(default_config, user_config)

    holiday = Holiday(merged_config)
    holiday.update_holidays_cache(datetime.today().year, datetime.today().month)

    # 다음 근무일 계산
    today = datetime.today().strftime('%Y%m%d')
    prvdDt = holiday.다음_근무일(today)

    print(f"\n{'='*60}")
    print(f"📅 오늘: {today}")
    print(f"📅 예약 대상일: {prvdDt}")
    print(f"{'='*60}")

    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        
        if action == 'reserve':
            test_reserve(merged_config, prvdDt)
        elif action == 'cancel':
            test_cancel(merged_config, prvdDt)
        elif action == 'both':
            # 예약 -> 취소 -> 다시 예약 테스트
            print("\n🔄 전체 테스트: 예약 -> 취소 -> 재예약")
            test_reserve(merged_config, prvdDt)
            input("\n⏸️ 취소하려면 Enter를 누르세요...")
            test_cancel(merged_config, prvdDt)
            input("\n⏸️ 다시 예약하려면 Enter를 누르세요...")
            test_reserve(merged_config, prvdDt)
        else:
            print("Usage: python test_reserve.py [reserve|cancel|both]")
    else:
        print("Usage: python test_reserve.py [reserve|cancel|both]")
        print("  reserve: 예약만 테스트")
        print("  cancel: 취소만 테스트")
        print("  both: 예약 -> 취소 -> 재예약 순서로 테스트")


if __name__ == '__main__':
    main()
