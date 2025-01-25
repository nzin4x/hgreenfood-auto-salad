import os
import sys
from datetime import datetime, timedelta

import yaml


def load_yaml(filename):

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
