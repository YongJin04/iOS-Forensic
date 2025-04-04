import re
from datetime import datetime, timezone, timedelta

def format_mac_time(mac_time):
    """
    macOS 기준 시간(2001년 1월 1일, UTC)에서부터 주어진 초(mac_time)를 더해 실제 날짜/시간으로 변환하고,
    한국 표준시(KST, GMT+9)로 변환하여 'YYYY년 M월 D일 요일 오전/오후 H:MM:SS GMT±zzzz' 형식의 문자열을 반환.
    만약 변환에 실패하면 "변환 실패 (mac_time)"를 반환.
    """
    try:
        mac_epoch = datetime(2001, 1, 1, tzinfo=timezone.utc)
        dt = mac_epoch + timedelta(seconds=mac_time)
        kst = dt.astimezone(timezone(timedelta(hours=9)))
        weekdays = {0: "월요일", 1: "화요일", 2: "수요일", 3: "목요일", 4: "금요일", 5: "토요일", 6: "일요일"}
        weekday_kor = weekdays[kst.weekday()]
        am_pm = kst.strftime("%p")
        if am_pm == "AM":
            am_pm = "오전"
        elif am_pm == "PM":
            am_pm = "오후"
        hour = int(kst.strftime("%I"))
        minute = kst.strftime("%M")
        second = kst.strftime("%S")
        formatted = f"{kst.year}년 {kst.month}월 {kst.day}일 {weekday_kor} {am_pm} {hour}:{minute}:{second} GMT{kst.strftime('%z')}"
        return formatted
    except:
        return f"변환 실패 ({mac_time})"

def format_phone_number(phone_str):
    """
    전화번호 문자열을 포맷팅하는 함수.
    - 전화번호가 암호화되어(숫자, +, -, 공백 외 문자가 포함된 경우) 있으면 원본 그대로 반환.
    - 전화번호가 "+82"로 시작하면, "+82"를 "0"으로 변경하여 국내 형식(예: 010-1234-5678)으로 포맷팅.
    - 숫자만 남겨 11자리이며 "010"으로 시작하면 xxx-xxxx-xxxx 형식으로 변환.
    - 그 외의 경우는 원본 문자열을 그대로 반환.
    """
    # 암호화된 전화번호 (숫자, +, -, 공백 외 문자가 있는 경우)는 그대로 반환
    if not re.fullmatch(r'[+\d\s-]+', phone_str.strip()):
        return phone_str

    phone_str = phone_str.strip()
    # 국제전화 형식 +82 처리: +82 다음에 0이 없으면 추가
    if phone_str.startswith("+82"):
        rest = phone_str[3:].strip()
        if not rest.startswith("0"):
            phone_str = "0" + rest
        else:
            phone_str = rest

    # 숫자만 남김
    digits = re.sub(r'\D', '', phone_str)
    if len(digits) == 11 and digits.startswith("010"):
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    return phone_str