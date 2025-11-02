# -*- coding: utf-8 -*-
"""
메인 프로그램 - 메뉴 시스템
"""
import os
import sys
import subprocess
from datetime import datetime

def clear_screen():
    """화면 지우기"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_banner():
    """배너 출력"""
    print("\n" + "="*60)
    print("🍽️ 현대오토에버 점심식단 자동 예약 프로그램")
    print("="*60)


def check_config_exists():
    """설정 파일 존재 여부 확인"""
    return os.path.exists('config.user.yaml')


def show_main_menu():
    """메인 메뉴 표시"""
    clear_screen()
    print_banner()
    
    config_exists = check_config_exists()
    
    print("\n📋 메뉴를 선택하세요:\n")
    print("1. 프로그램 시작 (자동 예약 실행)")
    
    if config_exists:
        print("2. 마스터 패스워드 변경")
        print("3. 환경 설정 재생성")
        print("4. 선호 식단 순서 변경")
        print("5. 예약 금지 날짜 관리 (휴가 등)")
    else:
        print("\n⚠️ 설정 파일이 없습니다. 먼저 초기 설정을 진행하세요.")
    
    print("0. 종료")
    print("\n" + "="*60)


def run_setup():
    """초기 설정 실행"""
    print("\n🔧 초기 설정을 시작합니다...\n")
    result = subprocess.run([sys.executable, "setup_config.py"])
    return result.returncode == 0


def run_app():
    """메인 프로그램 실행"""
    print("\n🚀 자동 예약 프로그램을 시작합니다...\n")
    subprocess.run([sys.executable, "app.py"])


def change_master_password():
    """마스터 패스워드 변경"""
    print("\n🔐 마스터 패스워드 변경\n")
    subprocess.run([sys.executable, "change_password.py"])


def recreate_config():
    """환경 설정 재생성"""
    print("\n⚠️ 환경 설정을 재생성하면 기존 설정이 백업됩니다.")
    confirm = input("계속하시겠습니까? (y/N): ")
    if confirm.lower() == 'y':
        run_setup()
    else:
        print("취소되었습니다.")


def change_menu_order():
    """선호 식단 순서 변경"""
    print("\n🍴 선호 식단 순서 변경\n")
    subprocess.run([sys.executable, "change_menu.py"])


def manage_vacation():
    """예약 금지 날짜 관리"""
    print("\n🏖️ 예약 금지 날짜 관리 (휴가 등)\n")
    subprocess.run([sys.executable, "manage_vacation.py"])


def main():
    """메인 함수"""
    while True:
        show_main_menu()
        
        # 설정 파일 존재 여부에 따라 메뉴 제한
        config_exists = check_config_exists()
        
        if config_exists:
            choice = input("\n선택 (1-5, 0=종료) [Enter=1]: ").strip() or "1"
        else:
            choice = input("\n먼저 초기 설정을 진행하세요 (1, 0=종료) [Enter=1]: ").strip() or "1"
        
        if choice == "0":
            print("\n👋 프로그램을 종료합니다.")
            break
        elif choice == "1":
            if not config_exists:
                if run_setup():
                    print("\n✅ 초기 설정이 완료되었습니다!")
                    input("\n계속하려면 Enter를 누르세요...")
                    run_app()
                else:
                    print("\n❌ 초기 설정에 실패했습니다.")
                    input("\n계속하려면 Enter를 누르세요...")
            else:
                run_app()
            break  # 프로그램 실행 후 종료
        elif choice == "2" and config_exists:
            change_master_password()
            input("\n계속하려면 Enter를 누르세요...")
        elif choice == "3" and config_exists:
            recreate_config()
            input("\n계속하려면 Enter를 누르세요...")
        elif choice == "4" and config_exists:
            change_menu_order()
            input("\n계속하려면 Enter를 누르세요...")
        elif choice == "5" and config_exists:
            manage_vacation()
            input("\n계속하려면 Enter를 누르세요...")
        else:
            print("\n❌ 잘못된 선택입니다.")
            input("\n계속하려면 Enter를 누르세요...")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 프로그램을 종료합니다.")
        sys.exit(0)
