# -*- coding: utf-8 -*-
"""
예약 금지 날짜 관리 (휴가 등)
"""
import os
from datetime import datetime, timedelta
from tinydb import TinyDB, Query

from config import DB_FILE

VACATION_TBL_NM = 'vacation'


def get_vacation_table():
    """휴가 테이블 가져오기"""
    db = TinyDB(DB_FILE, ensure_ascii=False, encoding='utf-8')
    return db.table(VACATION_TBL_NM)


def list_vacations():
    """휴가 목록 조회"""
    vacation_tbl = get_vacation_table()
    vacations = vacation_tbl.all()
    
    if not vacations:
        print("\n📭 등록된 예약 금지 날짜가 없습니다.\n")
        return []
    
    print("\n📋 예약 금지 날짜 목록:\n")
    print(f"{'번호':<4} {'날짜':<12} {'사유':<20} {'등록일'}")
    print("-" * 60)
    
    sorted_vacations = sorted(vacations, key=lambda x: x['date'])
    
    for idx, vac in enumerate(sorted_vacations, 1):
        date_str = vac['date']
        date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        reason = vac.get('reason', '-')
        created = vac.get('created_at', '-')
        
        # 날짜 비교 (과거/미래 표시)
        today = datetime.now().strftime('%Y%m%d')
        marker = "✓" if date_str < today else "📅"
        
        print(f"{idx:<4} {date_formatted:<12} {reason:<20} {created} {marker}")
    
    print("\n* ✓ = 지난 날짜\n")
    return sorted_vacations


def add_vacation():
    """휴가 날짜 추가"""
    print("\n➕ 예약 금지 날짜 추가\n")
    
    # 날짜 입력
    print("날짜를 입력하세요 (YYYYMMDD 또는 YYYY-MM-DD)")
    print("예시: 20251225 또는 2025-12-25")
    date_input = input("날짜: ").strip().replace("-", "")
    
    # 날짜 유효성 검증
    try:
        date_obj = datetime.strptime(date_input, '%Y%m%d')
        date_str = date_obj.strftime('%Y%m%d')
    except ValueError:
        print("❌ 올바른 날짜 형식이 아닙니다.")
        return False
    
    # 과거 날짜 확인
    today = datetime.now()
    if date_obj < today.replace(hour=0, minute=0, second=0, microsecond=0):
        print("⚠️ 과거 날짜입니다.")
        confirm = input("그래도 추가하시겠습니까? (y/N): ")
        if confirm.lower() != 'y':
            print("취소되었습니다.")
            return False
    
    # 사유 입력
    reason = input("사유 (선택, Enter=휴가): ").strip() or "휴가"
    
    # 중복 확인
    vacation_tbl = get_vacation_table()
    existing = vacation_tbl.search(Query().date == date_str)
    
    if existing:
        print(f"⚠️ {date_str}는 이미 등록되어 있습니다.")
        confirm = input("덮어쓰시겠습니까? (y/N): ")
        if confirm.lower() != 'y':
            print("취소되었습니다.")
            return False
        vacation_tbl.remove(Query().date == date_str)
    
    # 추가
    vacation_tbl.insert({
        'date': date_str,
        'reason': reason,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    
    date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    print(f"\n✅ {date_formatted} ({reason}) 추가되었습니다.")
    return True


def add_vacation_range():
    """휴가 기간 추가"""
    print("\n➕ 예약 금지 기간 추가\n")
    
    # 시작 날짜
    print("시작 날짜를 입력하세요 (YYYYMMDD 또는 YYYY-MM-DD)")
    start_input = input("시작 날짜: ").strip().replace("-", "")
    
    try:
        start_date = datetime.strptime(start_input, '%Y%m%d')
    except ValueError:
        print("❌ 올바른 날짜 형식이 아닙니다.")
        return False
    
    # 종료 날짜
    print("종료 날짜를 입력하세요 (YYYYMMDD 또는 YYYY-MM-DD)")
    end_input = input("종료 날짜: ").strip().replace("-", "")
    
    try:
        end_date = datetime.strptime(end_input, '%Y%m%d')
    except ValueError:
        print("❌ 올바른 날짜 형식이 아닙니다.")
        return False
    
    if start_date > end_date:
        print("❌ 시작 날짜가 종료 날짜보다 늦습니다.")
        return False
    
    # 사유 입력
    reason = input("사유 (선택, Enter=휴가): ").strip() or "휴가"
    
    # 날짜 범위 계산
    days = (end_date - start_date).days + 1
    print(f"\n총 {days}일을 추가합니다.")
    confirm = input("계속하시겠습니까? (y/N): ")
    if confirm.lower() != 'y':
        print("취소되었습니다.")
        return False
    
    # 날짜별로 추가
    vacation_tbl = get_vacation_table()
    current_date = start_date
    count = 0
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        
        # 중복 제거
        vacation_tbl.remove(Query().date == date_str)
        
        # 추가
        vacation_tbl.insert({
            'date': date_str,
            'reason': reason,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        count += 1
        current_date += timedelta(days=1)
    
    print(f"\n✅ {count}일이 추가되었습니다.")
    return True


def delete_vacation():
    """휴가 날짜 삭제"""
    vacations = list_vacations()
    
    if not vacations:
        return False
    
    print("\n🗑️ 삭제할 날짜의 번호를 입력하세요 (0=취소)")
    choice = input("번호: ").strip()
    
    if choice == "0":
        print("취소되었습니다.")
        return False
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(vacations):
            vacation = vacations[idx]
            date_str = vacation['date']
            date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
            
            confirm = input(f"'{date_formatted}'를 삭제하시겠습니까? (y/N): ")
            if confirm.lower() == 'y':
                vacation_tbl = get_vacation_table()
                vacation_tbl.remove(Query().date == date_str)
                print(f"✅ {date_formatted} 삭제되었습니다.")
                return True
            else:
                print("취소되었습니다.")
                return False
        else:
            print("❌ 올바른 번호가 아닙니다.")
            return False
    except ValueError:
        print("❌ 숫자를 입력하세요.")
        return False


def delete_past_vacations():
    """지난 날짜 일괄 삭제"""
    vacation_tbl = get_vacation_table()
    today = datetime.now().strftime('%Y%m%d')
    
    past_vacations = vacation_tbl.search(Query().date < today)
    
    if not past_vacations:
        print("\n📭 삭제할 지난 날짜가 없습니다.\n")
        return False
    
    print(f"\n🗑️ 지난 날짜 {len(past_vacations)}개를 삭제하시겠습니까?")
    confirm = input("계속하시겠습니까? (y/N): ")
    
    if confirm.lower() == 'y':
        vacation_tbl.remove(Query().date < today)
        print(f"✅ {len(past_vacations)}개의 지난 날짜가 삭제되었습니다.")
        return True
    else:
        print("취소되었습니다.")
        return False


def main():
    """메인 함수"""
    while True:
        print("\n" + "="*60)
        print("🏖️ 예약 금지 날짜 관리 (휴가 등)")
        print("="*60)
        
        list_vacations()
        
        print("\n📋 메뉴:")
        print("1. 날짜 추가")
        print("2. 기간 추가 (여러 날)")
        print("3. 날짜 삭제")
        print("4. 지난 날짜 일괄 삭제")
        print("0. 돌아가기")
        
        choice = input("\n선택 (1-4, 0=돌아가기): ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            add_vacation()
        elif choice == "2":
            add_vacation_range()
        elif choice == "3":
            delete_vacation()
        elif choice == "4":
            delete_past_vacations()
        else:
            print("\n❌ 잘못된 선택입니다.")
        
        input("\n계속하려면 Enter를 누르세요...")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 프로그램을 종료합니다.")
