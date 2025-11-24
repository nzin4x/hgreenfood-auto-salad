import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from holiday import Holiday

class TestScheduleLogic(unittest.TestCase):
    def setUp(self):
        self.config = {
            'data.go.kr': {
                'api': {
                    'key': 'dummy',
                    'holiday': {'endpoint': 'dummy'}
                }
            }
        }
        self.holiday = Holiday(self.config)
        # Mock get_cached_holidays to return empty list (no holidays)
        self.holiday.get_cached_holidays = MagicMock(return_value=([], None))

    @patch('holiday.datetime')
    def test_monday_morning(self, mock_datetime):
        # Monday 09:00 -> Action: Monday (Today), Target: Tuesday
        mock_datetime.now.return_value = datetime(2025, 1, 6, 9, 0, 0) # 2025-01-06 is Monday
        mock_datetime.strptime = datetime.strptime
        
        action_date = self.holiday.get_next_action_date()
        self.assertEqual(action_date, '20250106')
        
        target_date = self.holiday.get_target_service_date(action_date)
        self.assertEqual(target_date, '20250107')

    @patch('holiday.datetime')
    def test_monday_afternoon(self, mock_datetime):
        # Monday 14:00 -> Action: Tuesday (Tomorrow), Target: Wednesday
        mock_datetime.now.return_value = datetime(2025, 1, 6, 14, 0, 0)
        mock_datetime.strptime = datetime.strptime
        
        action_date = self.holiday.get_next_action_date()
        self.assertEqual(action_date, '20250107')
        
        target_date = self.holiday.get_target_service_date(action_date)
        self.assertEqual(target_date, '20250108')

    @patch('holiday.datetime')
    def test_friday_afternoon(self, mock_datetime):
        # Friday 14:00 -> Action: Monday (Next Week), Target: Tuesday
        mock_datetime.now.return_value = datetime(2025, 1, 10, 14, 0, 0) # 2025-01-10 is Friday
        mock_datetime.strptime = datetime.strptime
        
        action_date = self.holiday.get_next_action_date()
        self.assertEqual(action_date, '20250113') # Monday
        
        target_date = self.holiday.get_target_service_date(action_date)
        self.assertEqual(target_date, '20250114') # Tuesday

    @patch('holiday.datetime')
    def test_missed_reservation_check(self, mock_datetime):
        # Saturday 09:00 -> Should check Monday reservation
        # Nearest Future Workday: Monday (2025-01-13)
        # Previous Workday of Monday: Friday (2025-01-10)
        # Action Deadline: Friday 13:00
        # Now: Saturday 09:00 > Friday 13:00 -> MISSED!
        
        mock_datetime.now.return_value = datetime(2025, 1, 11, 9, 0, 0) # 2025-01-11 is Saturday
        mock_datetime.strptime = datetime.strptime
        
        nearest_workday = self.holiday.get_nearest_future_workday()
        self.assertEqual(nearest_workday, '20250113') # Monday
        
        previous_workday = self.holiday.get_previous_workday(nearest_workday)
        self.assertEqual(previous_workday, '20250110') # Friday

if __name__ == '__main__':
    unittest.main()
