import os

import os
import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)  # 실행 파일이 있는 폴더
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Python 스크립트가 있는 폴더

DB_FILE = os.path.join(BASE_DIR, "data.json")  # 실행 파일이 있는 폴더에 데이터 저장

RESERVATION_HISTORY_TBL_NM = 'ReservationHistory'
HOLIDAY_TBL_NM = 'holiday'
