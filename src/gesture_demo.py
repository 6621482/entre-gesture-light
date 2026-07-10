"""
gesture_demo.py

지금까지 만든 finger_state.py + gesture.py를 웹캠에 연결해서 실시간으로 ON/OFF 제스처를 판정하고,
프레임당 처리 시간(FPS)을 화면에 띄우는 데모 
"""

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import time

from finger_state import get_finger_ratios, get_finger_states
from gesture import classify_gesture

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

base_options = python.BaseOptions(model_asset_path="../hand_landmarker.task")
options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=2, running_mode=vision.RunningMode.VIDEO)
detector = vision.HandLandmarker.create_from_options(options)

def main():
    cap = cv2.VideoCapture(0)
    start_time = time.time()

    if not cap.isOpened():
        print("웹캠을 열 수 없습니다.")
        return
    
    while cap.isOpened():
        # < 프레임 처리 시간 측정 시작 > 
        fps_start_time = time.perf_counter()

        ret, frame = cap.read()
        if not ret:
            print("웹캠에서 프레임을 읽을 수 없습니다.")
            break

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        timestamp_ms = int((time.time() - start_time) * 1000)

        detection_result = detector.detect_for_video(mp_image, timestamp_ms)

        # < 프레임 처리 시간 측정 종료 >
        fps_end_time = time.perf_counter()
        fps_value = 1.0 / (fps_end_time - fps_start_time)

        if detection_result.hand_world_landmarks:
            # 1. 손가락 비율 계산
            hand_world_landmarks = detection_result.hand_world_landmarks[0]  # 첫 번째 손만 사용
            ratios = get_finger_ratios(hand_world_landmarks)

            # 2. 손가락 상태 판정
            finger_states = get_finger_states(ratios)

            # 3. 제스처 분류
            gesture_name = classify_gesture(finger_states)

            # 4. 제스처 이름 화면에 표시
            cv2.putText(
                frame, f"Gesture: {gesture_name}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                FONT_SIZE, (0, 255, 0), FONT_THICKNESS, cv2.LINE_AA,
            )
        
        cv2.putText(
                frame, f"FPS: {fps_value:.2f}",
                (10, 60), cv2.FONT_HERSHEY_SIMPLEX,
                FONT_SIZE, (0, 255, 0), FONT_THICKNESS, cv2.LINE_AA,
            )
        
        cv2.imshow("Gesture Demo", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    
if __name__ == "__main__":
    main()