import os
import sys
from datetime import datetime, timedelta

import yaml
from config import CONFIG_FILE

def set_ime_english():
    """Windows 콘솔에서 IME를 끄고(영문 입력) US 키보드 레이아웃으로 전환을 시도한다.
    - 실패해도 조용히 무시한다 (최선 시도)
    - 콘솔 포커스가 있어야 효과가 있다
    """
    if os.name != 'nt':
        return
    try:
        import ctypes

        user32 = ctypes.windll.user32
        imm32 = ctypes.windll.imm32

        hwnd = user32.GetForegroundWindow()

        # 1) IME 끄기 (한영 전환을 '영문' 상태로)
        hIMC = imm32.ImmGetContext(hwnd)
        if hIMC:
            imm32.ImmSetOpenStatus(hIMC, False)  # False = IME Off
            imm32.ImmReleaseContext(hwnd, hIMC)

        # 2) 키보드 레이아웃을 US English로 전환
        #    레이아웃 식별자: "00000409" (en-US)
        LoadKeyboardLayoutW = user32.LoadKeyboardLayoutW
        ActivateKeyboardLayout = user32.ActivateKeyboardLayout
        hkl = LoadKeyboardLayoutW("00000409", 1)  # KLF_ACTIVATE
        if hkl:
            ActivateKeyboardLayout(hkl, 0)
    except Exception:
        # 환경에 따라 실패할 수 있으므로 조용히 무시
        pass


def load_yaml(filename):
    # 환경 설정 파일인 경우 CONFIG_FILE 사용
    if filename == 'config.user.yaml':
        filename = CONFIG_FILE
    
    # load app.py path
    current_dir = os.path.dirname(sys.argv[0])  # 실행 파일 경로
    config_path = os.path.join(current_dir, filename)

    with open(config_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)


def merge_configs(default_config, user_config):
    # user_config 값이 있으면 default_config 값을 덮어씌움
    merged_config = default_config.copy()  # 기본 설정 복사
    merged_config.update(user_config)  # 사용자 설정으로 덮어씌움
    return merged_config


def 다음_근무일(날짜):
    현재날짜 = datetime.strptime(날짜, '%Y%m%d')
    다음날짜 = 현재날짜 + timedelta(days=1)

    while 다음날짜.weekday() >= 5:  # 5: Saturday, 6: Sunday
        다음날짜 += timedelta(days=1)

    return 다음날짜.strftime('%Y%m%d')


def already_done(response):
    return response.json()['errorMsg'] == '동일날짜에 이미 등록된 예약이 존재합니다.'
