import json
import os

import requests
from datetime import datetime, timedelta
import yaml

def load_yaml(filename):

    # load app.py path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, filename)

    with open(config_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

def merge_configs(default_config, user_config):
    # user_config 값이 있으면 default_config 값을 덮어씌움
    merged_config = default_config.copy()  # 기본 설정 복사
    merged_config.update(user_config)  # 사용자 설정으로 덮어씌움
    return merged_config

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
        # 쿠키 저장
        save_cookies(response.cookies, 'cookies.txt')
        return True  # 로그인 성공
    elif json.loads(response.content)['errorCode'] == -9995:
        print("비번이 틀립니다 5번 실패하면 잠겨버리니 앱에서 비번을 제대로 확인 하세요")
    elif  json.loads(response.content)['errorCode'] == 9903:
        print("비번이 계속 틀려 잠금 처리 됨, 앱에서 비번찾기/본인인증 해서 락을 푸세요")
    else:
        print(f"로그인 실패: {response.status_code}, {response.text}")
        return False  # 로그인 실패

def 다음_근무일(날짜):
    현재날짜 = datetime.strptime(날짜, '%Y%m%d')
    다음날짜 = 현재날짜 + timedelta(days=1)

    while 다음날짜.weekday() >= 5:  # 5: Saturday, 6: Sunday
        다음날짜 += timedelta(days=1)

    return 다음날짜.strftime('%Y%m%d')


def load_cookies(filename):
    cookies = {}
    with open(filename, 'r', encoding='utf-8') as cookie_file:
        for line in cookie_file:
            if line.strip():
                name, value = line.strip().split('=')
                cookies[name] = value
    return cookies

def 예약주문요청(config, conerDvCd):
    url = "https://hcafe.hgreenfood.com/api/menu/reservation/insertReservationOrder.do"
    headers = {
        "Content-Type": "application/json"
    }

    # prvdDt를 평일로 설정
    today = datetime.today().strftime('%Y%m%d')
    prvdDt = 다음_근무일(today)

    # JSON 데이터 구성
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

    # 쿠키 로드
    cookies = load_cookies('cookies.txt')

    # POST 요청 보내기
    response = requests.post(url, headers=headers, data=json.dumps(payload), cookies=cookies, verify=False)

    # 응답 코드 출력
    print(f"응답 코드: {response.status_code}")
    print(f"응답 내용: {response.json()}")

    return response

# 매핑 테이블 정의
menu_corner_map = {
    "샌": "0005",  # 샌드위치
    "샐": "0006",  # 샐러드
    "빵": "0007",  # 빵
    "닭": "0009"   # 닭가슴살
}

# 실행
def main():
    default_config = load_yaml('config.default.yaml')  # 기본 설정 YAML 파일 로드
    user_config = load_yaml('config.user.yaml')  # 사용자 설정 YAML 파일 로드

    merged_config = merge_configs(default_config, user_config)

    if not 로그인(merged_config):  # 로그인 실패 시 이후 로직 중단
        return  # 로그인 실패 시 종료

    # 사용자로부터 메뉴 입력
    menuSeq = merged_config['menuSeq']  # '샌,샐,빵,닭' 형태 가져오기
    menuInitials = [corner.strip() for corner in menuSeq.split(",")]  # ','로 분리

    for menuInitial in menuInitials:
        conerDvCd = menu_corner_map.get(menuInitial.strip())

        if conerDvCd:
            response = 예약주문요청(merged_config, conerDvCd)
            if response.status_code == 200:
                print(f"{menuInitial} 예약 요청 성공: {response.json()}")
                break  # 200 OK 응답이 오면 반복 종료
            else:
                print(f"{menuInitial} 예약 요청 실패: {response.status_code}, {response.text}")


if __name__ == '__main__':
    main()