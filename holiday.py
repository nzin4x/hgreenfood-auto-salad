import requests

from util import load_yaml

class Holiday:
    def __init__(self, config):
        self.config = config

    def get_holidays(self, year: int, month: int):
        # 요청할 파라미터 설정
        params = {
            'serviceKey': config['data.go.kr']['api']['key'],
            'pageNo': '1',
            'numOfRows': '10',
            'solYear': str(year),
            'solMonth': str(month).zfill(2)
        }

        # GET 요청
        response = requests.get(config['data.go.kr']['api']['holiday']['endpoint'], params=params)

        import xml.etree.ElementTree as ET

        # 주어진 XML 데이터
        xml_data = response.content

        # XML 파싱
        root = ET.fromstring(xml_data)

        # locdate 값을 저장할 리스트
        locdates = []

        # locdate 요소 추출
        for item in root.findall('.//item'):
            locdate = item.find('locdate').text
            locdates.append(locdate)

        return locdates


# API URL
config = load_yaml('config.user.yaml')

if __name__ == '__main__':
    holidays = Holiday(config).get_holidays(2025,10)
    print(holidays)




