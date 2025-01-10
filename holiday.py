import requests

from util import load_yaml

# API URL
url = 'http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getHoliDeInfo'

config = load_yaml('config.user.yaml')

# 요청할 파라미터 설정
params = {
    'serviceKey': config['data.go.kr-apikey'],
    'pageNo': '1',
    'numOfRows': '10',
    'solYear': '2025',
    'solMonth': '01'
}

# GET 요청
response = requests.get(url, params=params)

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

print(locdates)