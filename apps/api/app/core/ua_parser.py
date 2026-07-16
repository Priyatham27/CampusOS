import re

def parse_user_agent(ua_string: str) -> tuple[str, str, str]:
    """
    Deconstructs browser name, operating system, and platform category
    from a standard raw HTTP User-Agent header string.
    """
    if not ua_string:
        return "Unknown", "Unknown", "Unknown"

    ua = ua_string.lower()

    # 1. Platform Detection
    if any(keyword in ua for keyword in ["mobi", "iphone", "ipad", "android"]):
        if "ipad" in ua or "tablet" in ua:
            platform = "Tablet"
        else:
            platform = "Mobile"
    else:
        platform = "Desktop"

    # 2. Browser Detection
    if "edg/" in ua or "edge" in ua:
        browser = "Edge"
    elif "opr/" in ua or "opera" in ua:
        browser = "Opera"
    elif "chrome" in ua or "crios" in ua:
        browser = "Chrome"
    elif "firefox" in ua or "fxios" in ua:
        browser = "Firefox"
    elif "safari" in ua and "chrome" not in ua and "chromium" not in ua:
        browser = "Safari"
    else:
        browser = "Unknown Browser"

    # 3. Operating System Detection
    if "iphone" in ua or "ipad" in ua:
        os = "iOS"
    elif "android" in ua:
        os = "Android"
    elif "windows" in ua:
        os = "Windows"
    elif "macintosh" in ua or "mac os" in ua:
        os = "macOS"
    elif "linux" in ua:
        os = "Linux"
    else:
        os = "Unknown OS"

    return browser, os, platform
