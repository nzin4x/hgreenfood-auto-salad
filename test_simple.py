# -*- coding: utf-8 -*-
"""
간단한 예약 및 취소 테스트 스크립트 (휴일 API 없이)
"""
import json
import sys
from datetime import datetime, timedelta

import requests
import urllib3

from util import load_yaml, merge_configs

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 전역 세션 객체
session = requests.Session()

def 다음_근무일_간단(날짜_문자열):
    """간단한 다음 근무일 계산 (휴일 API 없이, 주말만 체크)"""
    날짜 = datetime.strptime(날짜_문자열, '%Y%m%d')
    지금 = datetime.now()
    
    # 13시 이전이면 오늘부터, 이후면 내일부터
    if 지금.hour < 13:
        시작날짜 = 날짜
    else:
        시작날짜 = 날짜 + timedelta(days=1)
    
    # 주말 건너뛰기
    while 시작날짜.weekday() >= 5:  # 5=토, 6=일
        시작날짜 += timedelta(days=1)
    
    return 시작날짜.strftime('%Y%m%d')


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

    try:
        response = session.post(url, headers=headers, data=json.dumps(payload), verify=False, timeout=10)
        result = response.json()
        
        if result.get('errorCode') == 0:
            print("✅ 로그인 성공")
            print(f"   사용자: {merged_config['userId']}")
            return True
        else:
            print(f"❌ 로그인 실패")
            print(f"   errorCode: {result.get('errorCode')}")
            print(f"   errorMsg: {result.get('errorMsg')}")
            return False
    except Exception as e:
        print(f"❌ 로그인 오류: {e}")
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

    try:
        response = session.post(url, headers=headers, data=json.dumps(payload), verify=False, timeout=10)
        
        print(f"📤 예약 응답 코드: {response.status_code}")
        result = response.json()
        print(f"📄 예약 응답:")
        print(f"   errorCode: {result.get('errorCode')}")
        print(f"   errorMsg: {result.get('errorMsg')}")
        
        return response
    except Exception as e:
        print(f"❌ 예약 요청 오류: {e}")
        return None


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

    try:
        response = session.post(url, headers=headers, data=json.dumps(payload), verify=False, timeout=10)
        
        print(f"📤 예약 조회 응답 코드: {response.status_code}")
        result = response.json()
        
        if result.get('errorCode') == 0:
            # dataSets.reserveList 구조 확인
            datasets = result.get('dataSets', {})
            reservations = datasets.get('reserveList', [])
            
            if reservations:
                print(f"📄 현재 예약 목록: {len(reservations)}건")
                for idx, res in enumerate(reservations, 1):
                    print(f"   [{idx}] {res.get('conerNm', 'N/A')} - {res.get('dispNm', 'N/A')}")
                    print(f"       예약일: {res.get('prvdDt', 'N/A')}, 상태: {res.get('rsvStatCd', 'N/A')}")
                return reservations
            else:
                print(f"   📭 예약 없음")
                return []
        else:
            print(f"   ❌ 조회 실패: {result.get('errorMsg')}")
            return []
    except Exception as e:
        print(f"❌ 예약 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return []


def 예약취소요청(reservation_data):
    """예약 취소 - 예약 데이터 전체를 받아서 취소"""
    url = "https://hcafe.hgreenfood.com/api/menu/reservation/updateMenuReservationCancel.do"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }

    # 예약 데이터를 그대로 사용 (취소에 필요한 모든 정보 포함)
    payload = reservation_data

    try:
        response = session.post(url, headers=headers, data=json.dumps(payload), verify=False, timeout=10)
        
        print(f"📤 취소 응답 코드: {response.status_code}")
        result = response.json()
        print(f"📄 취소 응답:")
        print(f"   errorCode: {result.get('errorCode')}")
        print(f"   errorMsg: {result.get('errorMsg')}")
        
        return response
    except Exception as e:
        print(f"❌ 취소 요청 오류: {e}")
        return None


menu_corner_map = {
    "샌": "0005",
    "샐": "0006",
    "빵": "0007",
    "헬": "0009",
    "닭": "0010"
}

menu_corner_name = {
    "샌": "샌드위치",
    "샐": "샐러드",
    "빵": "베이커리",
    "헬": "헬시세트",
    "닭": "닭가슴살"
}


def test_reserve(merged_config, prvdDt):
    """예약 테스트"""
    print(f"\n{'='*60}")
    print(f"🎯 예약 테스트: {prvdDt}")
    print(f"{'='*60}\n")

    if not 로그인(merged_config):
        return False

    menuSeq = merged_config.get('menuSeq', '샐,샌')
    menuInitials = [corner.strip() for corner in menuSeq.split(",")]
    
    print(f"\n선호 메뉴 순서: {', '.join([menu_corner_name.get(m, m) for m in menuInitials])}")

    for idx, menuInitial in enumerate(menuInitials, 1):
        conerDvCd = menu_corner_map.get(menuInitial.strip())

        if conerDvCd:
            print(f"\n[{idx}/{len(menuInitials)}] 🍴 {menu_corner_name.get(menuInitial, menuInitial)} (코드: {conerDvCd}) 예약 시도...")
            response = 예약주문요청(merged_config, conerDvCd, prvdDt)

            if not response:
                continue

            result = response.json()
            
            if response.status_code == 200 and result.get('errorCode') == 0:
                print(f"✅ {menu_corner_name.get(menuInitial, menuInitial)} 예약 성공!")
                return True
            elif result.get('errorMsg') == '동일날짜에 이미 등록된 예약이 존재합니다.':
                print(f"ℹ️ {menu_corner_name.get(menuInitial, menuInitial)} 이미 예약되어 있음")
                return True
            else:
                print(f"⚠️ {menu_corner_name.get(menuInitial, menuInitial)} 예약 실패")

    print("\n❌ 모든 메뉴 예약 실패")
    return False


def test_cancel(merged_config, prvdDt):
    """취소 테스트"""
    print(f"\n{'='*60}")
    print(f"🗑️ 취소 테스트: {prvdDt}")
    print(f"{'='*60}\n")

    if not 로그인(merged_config):
        return False

    # 먼저 예약 목록 조회
    reservations = 예약조회요청(prvdDt)
    
    if not reservations:
        print("\n⚠️ 취소할 예약이 없습니다.")
        return False
    
    # 첫 번째 예약 취소 (보통 1개만 있음)
    print(f"\n🗑️ {reservations[0].get('conerNm', 'N/A')} 예약 취소 시도...")
    response = 예약취소요청(reservations[0])

    if not response:
        return False

    result = response.json()
    
    # 취소 API는 errorCode가 1이면 성공!
    if response.status_code == 200 and result.get('errorCode') == 1:
        print(f"\n✅ 취소 성공!")
        return True
    else:
        print(f"\n❌ 취소 실패 (errorCode: {result.get('errorCode')})")
        return False


def main():
    default_config = load_yaml('config.default.yaml')
    user_config = load_yaml('config.user.yaml')
    merged_config = merge_configs(default_config, user_config)

    # 다음 근무일 계산 (간단 버전)
    today = datetime.today().strftime('%Y%m%d')
    prvdDt = 다음_근무일_간단(today)

    print(f"\n{'='*60}")
    print(f"📅 오늘: {today} ({datetime.today().strftime('%Y-%m-%d %A')})")
    print(f"📅 예약 대상일: {prvdDt}")
    print(f"⏰ 현재 시각: {datetime.now().strftime('%H:%M:%S')}")
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
            print("\nUsage: python test_simple.py [reserve|cancel|both]")
    else:
        print("\nUsage: python test_simple.py [reserve|cancel|both]")
        print("  reserve: 예약만 테스트")
        print("  cancel: 취소만 테스트")
        print("  both: 예약 -> 취소 -> 재예약 순서로 테스트")


if __name__ == '__main__':
    main()
