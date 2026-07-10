GESTURE = {
    "ON": {"엄지": True, "검지": True, "중지": True, "약지": True, "소지": True},
    "OFF": {"엄지": False, "검지": False, "중지": False, "약지": False, "소지": False},
}

# 손가락 상태 딕셔너리를 입력받아 제스처 이름을 반환. (없으면 "알 수 없음" 반환)
def classify_gesture(finger_states: dict[str, bool]) -> str:
    for gesture_name, gesture_states in GESTURE.items():
        if finger_states == gesture_states:
            return gesture_name
    return "알 수 없음" 