import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import time

# 랜드마크 인덱스 상수화 
WRIST = 0
FINGER_EXTENDED_THRESHOLD = 1.5
THUMB_EXTENDED_THRESHOLD = 1

FINGERS = {
    "검지": (5, 8),
    "중지": (9, 12),
    "약지": (13, 16),
    "소지": (17, 20),
}

# 엄지는 별도 블록 (기준점: pinky MCP) -> 엄지는 손바닥과 평행하게 움직이므로 다른 기준점이 필요함 
PINKY_MCP = 17  # 주먹을 쥐어도 손목에서 많이 안 멀어지므로 새끼손가락 (17번)을 기준으로 함
THUMB_MCP = 2
THUMB_TIP = 4

mp_hands = mp.tasks.vision.HandLandmarksConnections
mp_drawing = mp.tasks.vision.drawing_utils
mp_drawing_styles = mp.tasks.vision.drawing_styles

MARGIN = 10
FONT_SIZE = 1
FONT_THICKNESS = 1
HANDEDNESS_TEXT_COLOR = (88, 205, 54)

def draw_landmarks_on_image(rgb_image, detection_result):
    hand_landmarks_list = detection_result.hand_landmarks
    handedness_list = detection_result.handedness
    annotated_image = np.copy(rgb_image)

    for idx in range(len(hand_landmarks_list)):
        hand_landmarks = hand_landmarks_list[idx]
        handedness = handedness_list[idx]

        mp_drawing.draw_landmarks(
            annotated_image,
            hand_landmarks,
            mp_hands.HAND_CONNECTIONS,
            mp_drawing_styles.get_default_hand_landmarks_style(),
            mp_drawing_styles.get_default_hand_connections_style(),
        )

        height, width, _ = annotated_image.shape
        x_coordinates = [landmark.x for landmark in hand_landmarks]
        y_coordinates = [landmark.y for landmark in hand_landmarks]
        text_x = int(min(x_coordinates) * width)
        text_y = int(min(y_coordinates) * height) - MARGIN

        cv2.putText(
            annotated_image, f"{handedness[0].category_name}",
            (text_x, text_y), cv2.FONT_HERSHEY_DUPLEX,
            FONT_SIZE, HANDEDNESS_TEXT_COLOR, FONT_THICKNESS, cv2.LINE_AA,
        )
    return annotated_image

def calculate_distance(landmark1, landmark2):
    # landmark는 .x, .y, .z 속성을 가진 객체 (0~1 정규화된 값)
    # 유틀리드 거리 공식: sqrt((x2 - x1)^2 + (y2 - y1)^2 + (z2 - z1)^2)
    return np.sqrt((landmark2.x - landmark1.x) ** 2 + (landmark2.y - landmark1.y) ** 2 + (landmark2.z - landmark1.z) ** 2)

base_options = python.BaseOptions(model_asset_path="../hand_landmarker.task")
options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=2, running_mode=vision.RunningMode.VIDEO)
detector = vision.HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)
start_time = time.time()

if not cap.isOpened():
    print("웹캠을 열 수 없습니다.")
else:
    print("웹캠 연결 성공! 'q'를 누르면 종료됩니다.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("웹캠에서 프레임을 읽을 수 없습니다.")
        break

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    timestamp_ms = int((time.time() - start_time) * 1000)
    detection_result = detector.detect_for_video(mp_image, timestamp_ms)

    annotated_image = draw_landmarks_on_image(rgb_frame, detection_result)

    if detection_result.hand_world_landmarks:
        hand_world_landmarks = detection_result.hand_world_landmarks[0]  # 첫 번째 손의 랜드마크 가져오기
        wrist = hand_world_landmarks[WRIST]
        
        pinky_mcp = hand_world_landmarks[PINKY_MCP]
        thumb_mcp = hand_world_landmarks[THUMB_MCP]
        thumb_tip = hand_world_landmarks[THUMB_TIP]
            
        thumb_tip_dist = calculate_distance(pinky_mcp, thumb_tip)
        thumb_mcp_dist = calculate_distance(pinky_mcp, thumb_mcp)
        thumb_ratio = thumb_tip_dist / thumb_mcp_dist if thumb_mcp_dist != 0 else 0
    
        thumb_status = "펴짐" if thumb_ratio > THUMB_EXTENDED_THRESHOLD else "굽힘"
        print(f"엄지: {thumb_ratio:.2f} ({thumb_status})")

        for finger_name, (mcp_idx, tip_idx) in FINGERS.items():
            mcp = hand_world_landmarks[mcp_idx]
            tip = hand_world_landmarks[tip_idx]

            tip_dist = calculate_distance(wrist, tip)
            mcp_dist = calculate_distance(wrist, mcp)
            ratio = tip_dist / mcp_dist if mcp_dist != 0 else 0
            
            status = "펴짐" if ratio > FINGER_EXTENDED_THRESHOLD else "굽힘"
            print(f"{finger_name}: {ratio:.2f} ({status})")

    cv2.imshow("Hand Landmarker Webcam", cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR))

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()