THEMES = {
    "default": {"bg": "#f0f5ff", "primary": "#1d4ed8", "panel": "#ffffff"},
    "lesson_1": {"bg": "#e6f0ff", "primary": "#2563eb", "panel": "#ffffff"},
    "lesson_2": {"bg": "#eef2ff", "primary": "#4f46e5", "panel": "#ffffff"},
    "lesson_3": {"bg": "#eff6ff", "primary": "#0284c7", "panel": "#ffffff"},
    "lesson_4": {"bg": "#e0f2fe", "primary": "#0ea5e9", "panel": "#ffffff"},
    "lesson_5": {"bg": "#f0f9ff", "primary": "#0369a1", "panel": "#ffffff"},
    "lesson_6": {"bg": "#e0f2fe", "primary": "#0284c7", "panel": "#ffffff"},
}

def get_theme_for_lesson(lesson_id):
    """ คืนค่า theme ตาม lesson id """
    return THEMES.get(f"lesson_{lesson_id}", THEMES["default"])
