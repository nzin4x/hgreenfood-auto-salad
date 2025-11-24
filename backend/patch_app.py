# Script to add missing route to app.py
import re

app_py_path = "src/app.py"

with open(app_py_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the check-device handler section
pattern = r'(    if route == "/auth/check-device":\s+from auth_handler import check_device_handler\s+return check_device_handler\(event, _context\))'

# The routes to add
new_routes = '''
    if route == "/user/toggle-auto-reservation":
        from toggle_auto_reservation import toggle_auto_reservation_handler
        return toggle_auto_reservation_handler(event, _context)

    if route == "/user/delete-account":
        from delete_account import delete_account_handler
        return delete_account_handler(event, _context)

    if route == "/user/get-settings":
        from get_user_settings import get_user_settings_handler
        return get_user_settings_handler(event, _context)

    if route == "/user/update-settings":
        from update_user_settings import update_user_settings_handler
        return update_user_settings_handler(event, _context)

    if route == "/reservation/make-immediate":
        from immediate_reservation import immediate_reservation_handler
        return immediate_reservation_handler(event, _context)

    if route == "/admin/update-holidays":
        return update_holidays_handler(event, _context)'''

# Replace
new_content = re.sub(pattern, r'\1' + new_routes, content, count=1)

with open(app_py_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Routes added successfully!")
