import math

GESTURE = {
    "ON": {"엄지": True, "검지": True, "중지": True, "약지": True, "소지": True},
    "OFF": {"엄지": False, "검지": False, "중지": False, "약지": False, "소지": False},
    "밝기조절": {"엄지": True, "검지": True, "중지": False, "약지": False, "소지": False},
}

# 손가락 상태 딕셔너리를 입력받아 제스처 이름을 반환. (없으면 "알 수 없음" 반환)
def classify_gesture(finger_states: dict[str, bool]) -> str:
    for gesture_name, gesture_states in GESTURE.items():
        if finger_states == gesture_states:
            return gesture_name
    return "알 수 없음" 


# 엄지-검지 사이 거리(핀치)를 0~100 밝기 값으로 변환 
# world landmarks는 미터 단위라 카메라와의 거리에 영향받지 않음
def pinch_to_brightness(hand_world_landmarks, min_dist=0.02, max_dist=0.10):
    thumb_tip = hand_world_landmarks[4]
    index_tip = hand_world_landmarks[8]
    dist = math.dist((thumb_tip.x, thumb_tip.y, thumb_tip.z), (index_tip.x, index_tip.y, index_tip.z),)
    ratio = (dist-min_dist) / (max_dist-min_dist)
    ratio = max(0.0, min(1.0, ratio))
    return round(ratio * 100)