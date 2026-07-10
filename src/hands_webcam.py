import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import time

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

    # 1. BRG(OpenCV) -> RGB(Mediapipe)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # 2.numpy 배열을 mp.Image로 감싸기 (image.cread_from_file 대신)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

    # 3. 현재 타임스탬프 계산 (ms 단위, 단조 증가)
    timestamp_ms = int((time.time() - start_time) * 1000)

    # 4. VIDEO 모드 detect() 호출
    detection_result = detector.detect_for_video(mp_image, timestamp_ms)

    # 5. 결과 시각화
    annotated_image = draw_landmarks_on_image(rgb_frame, detection_result)

    # 6. RGB -> BGR(OpenCV)
    cv2.imshow("Hand Landmarker Webcam", cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR))

    # 7. 종료 조건: 'q' 키를 누르면 루프 탈출
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()