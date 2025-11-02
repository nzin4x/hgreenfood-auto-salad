# -*- coding: utf-8 -*-
"""
마스터 패스워드 변경
"""
import os
import sys
import getpass
import yaml
import base64
from setup_config import load_and_decrypt_config, encrypt_data, derive_key_from_password


def change_master_password():
    """마스터 패스워드 변경"""
    print("\n" + "="*60)
    print("🔐 마스터 패스워드 변경")
    print("="*60)
    
    if not os.path.exists('config.user.yaml'):
        print("\n❌ 설정 파일이 없습니다.")
        return False
    
    # 기존 마스터 패스워드 입력
    print("\n현재 마스터 패스워드를 입력하세요.")
    old_password = getpass.getpass("현재 마스터 패스워드: ")
    
    # 설정 파일 로드 및 복호화
    config = load_and_decrypt_config(old_password)
    
    if not config:
        print("\n❌ 현재 마스터 패스워드가 올바르지 않습니다.")
        return False
    
    print("✅ 현재 패스워드 확인 완료")
    
    # 새로운 마스터 패스워드 입력
    print("\n" + "-"*60)
    print("새로운 마스터 패스워드를 설정하세요.")
    print("⚠️ 최소 8자 이상이어야 합니다.")
    print("-"*60)
    
    while True:
        new_password = getpass.getpass("\n새 마스터 패스워드: ").strip()
        
        if len(new_password) < 8:
            print("   ⚠️ 마스터 패스워드는 최소 8자 이상이어야 합니다.")
            continue
        
        new_password_confirm = getpass.getpass("새 마스터 패스워드 확인: ").strip()
        
        if new_password == new_password_confirm:
            break
        else:
            print("   ❌ 패스워드가 일치하지 않습니다. 다시 입력해주세요.")
    
    # 새로운 Salt 생성
    new_salt = os.urandom(16)
    
    # 민감 정보 재암호화
    encrypted_password = encrypt_data(config['userData'], new_password, new_salt)
    encrypted_api_key = encrypt_data(config['data.go.kr']['api']['key'], new_password, new_salt)
    
    # 설정 파일 업데이트
    config['userData_encrypted'] = encrypted_password
    config['data.go.kr']['api']['key_encrypted'] = encrypted_api_key
    config['_salt'] = base64.b64encode(new_salt).decode()
    
    # 복호화된 데이터 제거 (암호화된 버전만 유지)
    if 'userData' in config:
        del config['userData']
    if 'key' in config.get('data.go.kr', {}).get('api', {}):
        del config['data.go.kr']['api']['key']
    
    # 저장
    with open('config.user.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    
    print("\n" + "="*60)
    print("✅ 마스터 패스워드가 변경되었습니다!")
    print("="*60)
    print("⚠️ 새 패스워드를 안전한 곳에 보관하세요.")
    print("   다음 실행부터 새 패스워드를 사용합니다.")
    print("="*60 + "\n")
    
    return True


def main():
    """메인 함수"""
    try:
        change_master_password()
    except KeyboardInterrupt:
        print("\n\n👋 취소되었습니다.")
        sys.exit(0)


if __name__ == '__main__':
    main()
