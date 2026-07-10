"""
finger_state.py

finger_extension_test.py에서 검증됐던 손가락 펴짐/굽힘 판정 로직을 그대로 옮긴 모듈
로직은 바꾸지 않았음 (순수 리팩터링) -> 다른 스크립트에서 import 해서 재사용하기 위한 분리

측정(get_finger_ratios)과 판단(get_finger_states)을 분리함:
- get_finger_ratios(landmarks) -> 손가락별 원본 비율 숫자 (재보정/디버깅용)
- get_finger_states(ratios) -> 그 비율을 threshold로 판정한 True/False (제스처 분류용)

원본과 동일한 설계:
- hand_world_landmarks 사용
- 엄지는 별도 처리: 손목이 아니라 pinky MCP를 기준점으로 삼음
"""

import numpy as np

# 랜드마크 인덱스 (MediaPipe 21포인트 규격)
WRIST = 0
PINKY_MCP = 17
THUMB_MCP = 2
THUMB_TIP = 4

FINGERS = {
    "검지": (5, 8),
    "중지": (9, 12),
    "약지": (13, 16),
    "소지": (17, 20),
}

FINGER_EXTENDED_THRESHOLD = 1.5
THUMB_EXTENDED_THRESHOLD = 1.25

def calculate_distance(landmark1, landmark2) -> float:
    """두 랜드마크 사이의 유클리드 거리. landmark는 .x, .y, .z 속성을 가진 객체."""
    return np.sqrt(
        (landmark2.x - landmark1.x) ** 2
        + (landmark2.y - landmark1.y) ** 2
        + (landmark2.z - landmark1.z) ** 2
    )

def get_finger_ratios(hand_world_landmarks) -> dict[str, float]:
    """한 손의 world landmarks를 받아서 손가락별 (tip거리/mcp거리) 비율을 딕셔너리로 반환.

    판정(True/False) 없이 순수 측정값만 반환 — 재보정/디버깅 시 원본 숫자를 보기 위함.
    반환 예: {"엄지": 1.23, "검지": 0.87, "중지": 1.61, "약지": 1.55, "소지": 0.42}
    """
    wrist = hand_world_landmarks[WRIST]
    pinky_mcp = hand_world_landmarks[PINKY_MCP]

    ratios: dict[str, float] = {}

    # 엄지: pinky_mcp 기준
    thumb_mcp = hand_world_landmarks[THUMB_MCP]
    thumb_tip = hand_world_landmarks[THUMB_TIP]
    thumb_tip_dist = calculate_distance(pinky_mcp, thumb_tip)
    thumb_mcp_dist = calculate_distance(pinky_mcp, thumb_mcp)
    ratios["엄지"] = thumb_tip_dist / thumb_mcp_dist if thumb_mcp_dist != 0 else 0

    # 나머지 네 손가락: wrist 기준
    for finger_name, (mcp_idx, tip_idx) in FINGERS.items():
        mcp = hand_world_landmarks[mcp_idx]
        tip = hand_world_landmarks[tip_idx]
        tip_dist = calculate_distance(wrist, tip)
        mcp_dist = calculate_distance(wrist, mcp)
        ratios[finger_name] = tip_dist / mcp_dist if mcp_dist != 0 else 0

    return ratios


def get_finger_states(ratios: dict[str, float]) -> dict[str, bool]:
    """get_finger_ratios()가 반환한 비율 딕셔너리를 입력받아 펴짐(True)/굽힘(False)으로 판정.

    반환 예: {"엄지": True, "검지": False, "중지": False, "약지": False, "소지": False}
    (주먹 쥔 상태에서 엄지만 삐져나온 경우 등)
    """
    states: dict[str, bool] = {}
    for finger_name, ratio in ratios.items():
        threshold = THUMB_EXTENDED_THRESHOLD if finger_name == "엄지" else FINGER_EXTENDED_THRESHOLD
        states[finger_name] = ratio > threshold
    return states