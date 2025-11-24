# -*- coding: utf-8 -*-
"""
설정 관리 프로그램
- 최초 실행 시 사용자 정보 입력
- 민감 정보는 마스터 패스워드로 암호화
- 입력값 유효성 검증
"""
import os
import sys
import getpass
import yaml
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import json
import requests
from datetime import datetime

# SSL 경고 무시
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """패스워드로부터 암호화 키 생성"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def encrypt_data(data: str, password: str, salt: bytes) -> str:
    """데이터 암호화"""
    key = derive_key_from_password(password, salt)
    f = Fernet(key)
    return f.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str, password: str, salt: bytes) -> str:
    """데이터 복호화"""
    key = derive_key_from_password(password, salt)
    f = Fernet(key)
    return f.decrypt(encrypted_data.encode()).decode()


def validate_login(user_id: str, user_password: str) -> bool:
    """로그인 정보 검증"""
    print("\n🔐 로그인 정보 검증 중...")
    
    url = "https://hcafe.hgreenfood.com/api/com/login.do"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "userId": user_id,
        "userData": user_password,
        "osDvCd": "",
        "userCurrAppVer": "1.2.3",
        "mobiPhTrmlId": ""
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), 
                                verify=False, timeout=10)
        result = response.json()
        
        if result.get('errorCode') == 0:
            print("   ✅ 로그인 성공!")
            return True
        else:
            print(f"   ❌ 로그인 실패: {result.get('errorMsg')}")
            return False
    except Exception as e:
        print(f"   ❌ 로그인 검증 오류: {e}")
        return False


def validate_holiday_api(api_key: str) -> bool:
    """휴일 API 키 검증"""
    print("\n🗓️ 휴일 API 키 검증 중...")
    
    url = "http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo"
    
    # data.go.kr 샘플 코드와 동일하게 params 사용
    params = {
        'serviceKey': api_key,
        'solYear': str(datetime.now().year),
        'solMonth': str(datetime.now().month).zfill(2)
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            import xml.etree.ElementTree as ET
            try:
                root = ET.fromstring(response.content)
                # 에러 코드 확인
                result_code = root.find('.//resultCode')
                if result_code is not None and result_code.text == '00':
                    print("   ✅ 휴일 API 키 유효!")
                    return True
                else:
                    result_msg = root.find('.//resultMsg')
                    msg = result_msg.text if result_msg is not None else 'Unknown'
                    print(f"   ❌ API 응답 오류: {result_code.text if result_code is not None else 'Unknown'}")
                    print(f"      메시지: {msg}")
                    return False
            except ET.ParseError:
                print("   ❌ API 응답 파싱 실패")
                print(f"      응답: {response.text[:200]}")
                return False
        else:
            print(f"   ❌ API 호출 실패: {response.status_code}")
            if response.status_code == 403:
                print("      💡 data.go.kr 사이트에서 '특일정보조회서비스' 활용신청이 승인되었는지 확인하세요")
            elif response.status_code == 401:
                print("      💡 API 키가 올바른지 확인하거나 data.go.kr에서 활용신청 승인 상태를 확인하세요")
            print("      ℹ️ 검증 실패해도 프로그램은 동작합니다 (공휴일 체크만 제한적)")
            return False
    except Exception as e:
        print(f"   ❌ API 검증 오류: {e}")
        return False


def create_config():
    """설정 파일 생성"""
    print("\n" + "="*60)
    print("🎯 사내 식당 자동 예약 프로그램 - 초기 설정")
    print("="*60)
    
    print("\n📌 설정 정보를 입력해주세요.")
    print("   (민감 정보는 마스터 패스워드로 암호화되어 저장됩니다)\n")
    
    # 1. 사용자 ID
    while True:
        user_id = input("1️⃣ 사용자 ID: ").strip()
        if user_id:
            break
        print("   ⚠️ ID를 입력해주세요.")
    
    # 2. 사용자 비밀번호
    while True:
        user_password = getpass.getpass("2️⃣ 사용자 비밀번호: ").strip()
        if user_password:
            break
        print("   ⚠️ 비밀번호를 입력해주세요.")
    
    # 로그인 검증
    if not validate_login(user_id, user_password):
        print("\n❌ 로그인 정보가 올바르지 않습니다. 처음부터 다시 시작해주세요.")
        return False
    
    # 3. data.go.kr API 키
    print("\n3️⃣ data.go.kr 휴일 데이터 조회 API 키")
    print("   (https://www.data.go.kr 에서 발급)")
    print("   💡 팁: 'Encoding' 또는 'Decoding' 버전 모두 사용 가능")
    while True:
        api_key = input("   API Key: ").strip()
        if api_key:
            break
        print("   ⚠️ API 키를 입력해주세요.")
    
    # API 키 검증 (선택 사항)
    print("\n   API 키를 검증하시겠습니까? (y/N): ", end='')
    if input().lower() == 'y':
        if not validate_holiday_api(api_key):
            print("\n⚠️ API 키 검증 실패.")
            print("   📌 확인 사항:")
            print("      1. data.go.kr → 나의 API → 개인 API인증키에서 키 값 확인")
            print("      2. data.go.kr → 활용신청 → '특일정보' 서비스 승인 상태 확인")
            print("      3. 신청 직후에는 승인까지 1-2일 소요될 수 있음")
            print("\n   ℹ️ 공휴일 API 없이도 프로그램은 정상 작동합니다!")
            print("      (단, 공휴일에도 예약 시도를 하게 되며 최대 10회 재시도 후 포기)")
            print("\n   그래도 계속하시겠습니까? (Y/n): ", end='')
            if input().lower() == 'n':
                return False
    else:
        print("   ⏭️ API 키 검증을 건너뜁니다.")
    
    # 4. 선호 메뉴 순서
    print("\n4️⃣ 선호 메뉴 순서를 입력하세요")
    print("   (샌: 샌드위치, 샐: 샐러드, 빵: 베이커리, 헬: 헬시세트, 닭: 닭가슴살)")
    print("   예시: 샌,샐,빵")
    
    while True:
        menu_seq = input("   선호 메뉴 순서: ").strip()
        if menu_seq:
            # 유효성 검증
            valid_menus = ['샌', '샐', '빵', '헬', '닭']
            menus = [m.strip() for m in menu_seq.split(',')]
            if all(m in valid_menus for m in menus):
                break
            else:
                print(f"   ⚠️ 올바른 메뉴를 입력하세요. (가능: {', '.join(valid_menus)})")
        else:
            print("   ⚠️ 메뉴를 입력해주세요.")
    
    # 5. 배달 층
    print("\n5️⃣ 배달받을 층을 입력하세요")
    print("   예시: 5층, 10층")
    
    while True:
        floor = input("   배달 층: ").strip()
        if floor:
            break
        print("   ⚠️ 층을 입력해주세요.")
    
    # 6. 마스터 패스워드 설정
    print("\n" + "="*60)
    print("🔐 마스터 패스워드 설정")
    print("="*60)
    print("⚠️ 중요: 이 패스워드는 민감 정보를 암호화하는데 사용됩니다.")
    print("         프로그램 실행 시마다 필요하므로 잊어버리지 마세요!")
    print("         (분실 시 설정을 처음부터 다시 해야 합니다)\n")
    
    while True:
        master_password = getpass.getpass("마스터 패스워드 입력: ").strip()
        if len(master_password) < 8:
            print("   ⚠️ 마스터 패스워드는 최소 8자 이상이어야 합니다.")
            continue
        
        master_password_confirm = getpass.getpass("마스터 패스워드 확인: ").strip()
        
        if master_password == master_password_confirm:
            break
        else:
            print("   ❌ 패스워드가 일치하지 않습니다. 다시 입력해주세요.")
    
    # Salt 생성 (고정값 - 파일에 저장됨)
    salt = os.urandom(16)
    
    # 민감 정보 암호화
    encrypted_password = encrypt_data(user_password, master_password, salt)
    encrypted_api_key = encrypt_data(api_key, master_password, salt)
    
    # 설정 파일 생성
    config = {
        'userId': user_id,
        'userData_encrypted': encrypted_password,
        'menuSeq': menu_seq,
        'floorNm': floor,
        'data.go.kr': {
            'api': {
                'key_encrypted': encrypted_api_key,
                'holiday': {
                    'endpoint': 'http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo'
                }
            }
        },
        'reserve': {
            'at': {
                'hour': 13,
                'minute': 0,
                'second': 0
            }
        },
        '_salt': base64.b64encode(salt).decode(),
        '_encrypted': True
    }
    
    # 파일 저장
    with open('config.user.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    
    # Windows Credential Manager에 마스터 패스워드 저장
    try:
        import keyring
        keyring.set_password("hgreenfood-auto-salad", "master_password", master_password)
        print("\n🔐 마스터 패스워드가 Windows 자격 증명 관리자에 저장되었습니다.")
        print("   (이제 프로그램 실행 시 패스워드를 입력하지 않아도 됩니다)")
    except Exception as e:
        print(f"\n⚠️ Windows 자격 증명 관리자 저장 실패: {e}")
        print("   (프로그램 실행 시마다 패스워드를 입력해야 합니다)")
    
    print("\n" + "="*60)
    print("✅ 설정 파일이 생성되었습니다!")
    print("="*60)
    print(f"📁 파일 위치: {os.path.abspath('config.user.yaml')}")
    print("🔒 민감 정보는 암호화되어 저장되었습니다.")
    print("\n⚠️ 주의사항:")
    print("   1. 마스터 패스워드를 안전한 곳에 보관하세요")
    print("   2. config.user.yaml 파일은 절대 공유하지 마세요")
    print("   3. Git에 커밋되지 않도록 .gitignore에 포함되어 있습니다")
    print("\n🚀 이제 'python app.py' 명령으로 프로그램을 실행할 수 있습니다.")
    print("="*60 + "\n")
    
    return True


def load_and_decrypt_config(master_password: str):
    """설정 파일 로드 및 복호화"""
    if not os.path.exists('config.user.yaml'):
        return None
    
    with open('config.user.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    if not config.get('_encrypted'):
        # 암호화되지 않은 구 버전
        return config
    
    # Salt 복원
    salt = base64.b64decode(config['_salt'])
    
    # 복호화
    try:
        config['userData'] = decrypt_data(config['userData_encrypted'], master_password, salt)
        config['data.go.kr']['api']['key'] = decrypt_data(
            config['data.go.kr']['api']['key_encrypted'], 
            master_password, 
            salt
        )
        return config
    except Exception as e:
        print(f"❌ 복호화 실패: 마스터 패스워드가 올바르지 않습니다.")
        return None


def main():
    """메인 함수"""
    if os.path.exists('config.user.yaml'):
        print("\n⚠️ 설정 파일이 이미 존재합니다.")
        print("   새로 만들려면 기존 파일을 삭제하거나 백업하세요.")
        print(f"   파일 위치: {os.path.abspath('config.user.yaml')}\n")
        
        response = input("기존 설정을 덮어쓰시겠습니까? (y/N): ")
        if response.lower() != 'y':
            print("설정 생성이 취소되었습니다.")
            return
        
        # 기존 파일 백업
        import shutil
        backup_name = f"config.user.yaml.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy('config.user.yaml', backup_name)
        print(f"✅ 기존 설정이 백업되었습니다: {backup_name}\n")
    
    # 설정 생성
    success = create_config()
    
    if not success:
        print("\n❌ 설정 생성에 실패했습니다.")
        sys.exit(1)


if __name__ == '__main__':
    main()
