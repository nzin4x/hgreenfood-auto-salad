# -*- coding: utf-8 -*-
"""
선호 식단 순서 변경
"""
import os
import sys
import getpass
import yaml
from setup_config import load_and_decrypt_config, encrypt_data
import base64


def change_menu_order():
    """선호 식단 순서 변경"""
    print("\n" + "="*60)
    print("🍴 선호 식단 순서 변경")
    print("="*60)
    
    if not os.path.exists('config.user.yaml'):
        print("\n❌ 설정 파일이 없습니다.")
        return False
    
    # 마스터 패스워드 입력
    print("\n🔐 마스터 패스워드를 입력하세요.")
    master_password = getpass.getpass("마스터 패스워드: ")
    
    # 설정 파일 로드 및 복호화
    config = load_and_decrypt_config(master_password)
    
    if not config:
        print("\n❌ 마스터 패스워드가 올바르지 않습니다.")
        return False
    
    print("\n✅ 설정 파일 로드 완료")
    
    # 현재 설정 표시
    print("\n📋 현재 선호 메뉴 순서:")
    current_menu = config.get('menuSeq', '')
    print(f"   {current_menu}")
    
    menu_name_map = {
        '샌': '샌드위치',
        '샐': '샐러드',
        '빵': '베이커리',
        '헬': '헬시세트',
        '닭': '닭가슴살'
    }
    
    menus = [m.strip() for m in current_menu.split(',') if m.strip()]
    print(f"   → {', '.join([menu_name_map.get(m, m) for m in menus])}")
    
    # 새로운 순서 입력
    print("\n🔄 새로운 선호 메뉴 순서를 입력하세요")
    print("   (샌: 샌드위치, 샐: 샐러드, 빵: 베이커리, 헬: 헬시세트, 닭: 닭가슴살)")
    print("   예시: 샌,샐,빵")
    print("   (Enter = 변경 취소)")
    
    new_menu = input("\n   선호 메뉴 순서: ").strip()
    
    if not new_menu:
        print("\n취소되었습니다.")
        return False
    
    # 유효성 검증
    valid_menus = ['샌', '샐', '빵', '헬', '닭']
    new_menus = [m.strip() for m in new_menu.split(',')]
    
    if not all(m in valid_menus for m in new_menus):
        print(f"\n❌ 올바른 메뉴를 입력하세요. (가능: {', '.join(valid_menus)})")
        return False
    
    # 확인
    print(f"\n새로운 순서: {', '.join([menu_name_map.get(m, m) for m in new_menus])}")
    confirm = input("변경하시겠습니까? (y/N): ")
    
    if confirm.lower() != 'y':
        print("취소되었습니다.")
        return False
    
    # 설정 파일 업데이트
    config['menuSeq'] = new_menu
    
    # 저장
    with open('config.user.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    
    print("\n✅ 선호 메뉴 순서가 변경되었습니다!")
    return True


def main():
    """메인 함수"""
    try:
        change_menu_order()
    except KeyboardInterrupt:
        print("\n\n👋 취소되었습니다.")
        sys.exit(0)


if __name__ == '__main__':
    main()
