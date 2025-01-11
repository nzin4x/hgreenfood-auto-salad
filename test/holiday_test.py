import pytest

from holiday import Holiday
from util import load_yaml


@pytest.fixture
def userconfig():
    yield  load_yaml('config.user.yaml')

def test_holiday_api(userconfig):
    holidays = Holiday(userconfig).get_holidays(2025, 1)
    assert '20250127' in holidays
    holidays = Holiday(userconfig).get_holidays(2025, 10)
    assert '20251005' in holidays
