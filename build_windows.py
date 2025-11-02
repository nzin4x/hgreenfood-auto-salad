# -*- coding: utf-8 -*-
"""
Windows용 실행 파일 빌드 스크립트
PyInstaller를 사용하여 dist 폴더에 exe 파일 생성
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path


def print_banner():
    """배너 출력"""
    print("\n" + "="*70)
    print("🏗️ 현대오토에버 점심식단 자동 예약 프로그램 - Windows 빌드")
    print("="*70)


def check_pyinstaller():
    """PyInstaller 설치 확인"""
    print("\n📦 PyInstaller 확인 중...")
    try:
        import PyInstaller
        print(f"   ✅ PyInstaller {PyInstaller.__version__} 설치됨")
        return True
    except ImportError:
        print("   ❌ PyInstaller가 설치되어 있지 않습니다.")
        print("\n설치하시겠습니까? (y/N): ", end='')
        choice = input().strip().lower()
        
        if choice == 'y':
            print("\n📥 PyInstaller 설치 중...")
            result = subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("   ✅ PyInstaller 설치 완료")
                return True
            else:
                print(f"   ❌ 설치 실패: {result.stderr}")
                return False
        else:
            print("빌드를 취소합니다.")
            return False


def clean_build():
    """이전 빌드 파일 정리"""
    print("\n🧹 이전 빌드 파일 정리 중...")
    
    folders_to_clean = ['build', 'dist', '__pycache__']
    files_to_clean = ['*.spec']
    
    for folder in folders_to_clean:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"   🗑️ {folder}/ 삭제됨")
    
    # .spec 파일 삭제
    for spec_file in Path('.').glob('*.spec'):
        spec_file.unlink()
        print(f"   🗑️ {spec_file} 삭제됨")
    
    print("   ✅ 정리 완료")


def create_spec_file():
    """PyInstaller spec 파일 생성"""
    print("\n📝 빌드 설정 파일 생성 중...")
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 메인 프로그램 (초기 설정 통합)
main_a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.default.yaml', '.'),
    ],
    hiddenimports=['cryptography', 'tinydb', 'yaml', 'requests'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

main_pyz = PYZ(main_a.pure, main_a.zipped_data, cipher=block_cipher)

main_exe = EXE(
    main_pyz,
    main_a.scripts,
    main_a.binaries,
    main_a.zipfiles,
    main_a.datas,
    [],
    name='HGreenfoodAutoReservation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# 테스트 유틸리티
test_a = Analysis(
    ['test_simple.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['cryptography', 'tinydb', 'yaml', 'requests'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

test_pyz = PYZ(test_a.pure, test_a.zipped_data, cipher=block_cipher)

test_exe = EXE(
    test_pyz,
    test_a.scripts,
    test_a.binaries,
    test_a.zipfiles,
    test_a.datas,
    [],
    name='test_simple',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''
    
    with open('hgreenfood.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("   ✅ hgreenfood.spec 생성 완료")


def build_executable():
    """실행 파일 빌드"""
    print("\n🔨 실행 파일 빌드 중...")
    print("   ⏳ 시간이 걸릴 수 있습니다. 잠시만 기다려주세요...\n")
    
    # PyInstaller 실행
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "hgreenfood.spec", "--clean"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("\n   ✅ 빌드 성공!")
        return True
    else:
        print(f"\n   ❌ 빌드 실패:")
        print(result.stderr)
        return False


def copy_additional_files():
    """추가 파일 복사"""
    print("\n📋 추가 파일 복사 중...")
    
    files_to_copy = [
        'config.default.yaml',
        'README.md',
        'USER_GUIDE.md',
    ]
    
    dist_dir = Path('dist')
    
    for file in files_to_copy:
        if os.path.exists(file):
            shutil.copy(file, dist_dir / file)
            print(f"   📄 {file} → dist/")
    
    print("   ✅ 파일 복사 완료")


def create_readme():
    """dist용 README 생성"""
    print("\n📝 실행 가이드 생성 중...")
    
    readme_content = '''# 🍽️ 현대오토에버 점심식단 자동 예약 프로그램

## 🚀 빠른 시작

### Windows

1. `HGreenfoodAutoReservation.exe` 실행
2. 최초 실행 시 자동으로 초기 설정 시작
3. 설정 완료 후 자동으로 예약 프로그램 실행

### 메인 메뉴

```
1. 프로그램 시작 (자동 예약 실행) - Enter=기본값
2. 마스터 패스워드 변경
3. 환경 설정 재생성
4. 선호 식단 순서 변경
5. 예약 금지 날짜 관리 (휴가 등)
0. 종료
```

## 📁 포함된 파일

- `HGreenfoodAutoReservation.exe` - 메인 프로그램 (초기 설정 포함)
- `test_simple.exe` - 테스트 도구
- `config.default.yaml` - 기본 설정 파일
- `README.md` - 전체 문서
- `USER_GUIDE.md` - 상세 사용자 가이드

## 🔧 초기 설정

프로그램을 처음 실행하면 자동으로 초기 설정이 시작되며, 다음 정보를 입력합니다:

1. 사용자 ID
2. 사용자 비밀번호
3. data.go.kr API 키
4. 선호 메뉴 순서 (예: 샌,샐,빵)
5. 배달받을 층
6. 마스터 패스워드 (8자 이상)

## 🍴 메뉴 코드

- `샌` : 샌드위치
- `샐` : 샐러드
- `빵` : 베이커리
- `헬` : 헬시세트
- `닭` : 닭가슴살

## 🏖️ 휴가 관리

메뉴 5번에서 예약하지 않을 날짜를 등록할 수 있습니다.

## ⚠️ 주의사항

1. **마스터 패스워드를 분실하면 설정을 재생성해야 합니다**
2. `config.user.yaml` 파일을 공유하지 마세요
3. 13시에 PC가 켜져있어야 예약이 됩니다
4. PC 수면 모드를 해제해 두세요

## 📊 로그 확인

프로그램 실행 후 `app.log` 파일에서 실행 로그를 확인할 수 있습니다.

## 🧪 테스트

예약/취소를 테스트하려면:

```
test_simple.exe reserve  # 예약 테스트
test_simple.exe cancel   # 취소 테스트
```

## 📞 문제 해결

### 로그인 실패
- ID/PW 확인
- 메뉴 3번(환경 설정 재생성)으로 재설정

### 마스터 패스워드 잊어버림
- 메뉴 3번(환경 설정 재생성)으로 재설정

### 예약이 안됨
- 13시에 PC가 켜져있는지 확인
- app.log 파일 확인
- 휴가 날짜로 등록되지 않았는지 확인

---

**상세한 내용은 USER_GUIDE.md를 참조하세요.**
'''
    
    with open('dist/시작하기.txt', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("   ✅ dist/시작하기.txt 생성 완료")


def show_summary():
    """빌드 결과 요약"""
    print("\n" + "="*70)
    print("✅ 빌드 완료!")
    print("="*70)
    
    dist_dir = Path('dist')
    
    print(f"\n📦 생성된 파일 목록 (dist 폴더):\n")
    
    exe_files = list(dist_dir.glob('*.exe'))
    other_files = [f for f in dist_dir.iterdir() if f.suffix != '.exe']
    
    # 실행 파일
    print("  🚀 실행 파일:")
    for exe in sorted(exe_files):
        size_mb = exe.stat().st_size / (1024 * 1024)
        print(f"     • {exe.name:<35} ({size_mb:.1f} MB)")
    
    # 기타 파일
    print("\n  📄 기타 파일:")
    for file in sorted(other_files):
        if file.is_file():
            size_kb = file.stat().st_size / 1024
            print(f"     • {file.name:<35} ({size_kb:.1f} KB)")
    
    print("\n" + "="*70)
    print("🎯 다음 단계:")
    print("="*70)
    print("\n1. dist 폴더로 이동")
    print("   cd dist")
    print("\n2. 메인 프로그램 실행")
    print("   HGreenfoodAutoReservation.exe")
    print("\n3. 또는 폴더 전체를 다른 PC로 복사하여 사용")
    print("\n⚠️ config.user.yaml 파일은 개인정보이므로 공유하지 마세요!")
    print("="*70 + "\n")


def main():
    """메인 함수"""
    print_banner()
    
    # 1. PyInstaller 확인
    if not check_pyinstaller():
        return
    
    # 2. 이전 빌드 정리
    clean_build()
    
    # 3. Spec 파일 생성
    create_spec_file()
    
    # 4. 빌드 실행
    if not build_executable():
        print("\n❌ 빌드에 실패했습니다.")
        return
    
    # 5. 추가 파일 복사
    copy_additional_files()
    
    # 6. 실행 가이드 생성
    create_readme()
    
    # 7. 요약 출력
    show_summary()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 빌드가 취소되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
