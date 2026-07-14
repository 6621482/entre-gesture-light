import cv2
import csv
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
THRESHOLD_TEXT_COLOR = (0, 255, 255)

FINGER_ORDER = ["엄지", "검지", "중지", "약지", "소지"]

# ---------------------------------------------------------
# 실험 파라미터: 여기 값만 바꿔가며 재실행
# 방법: 하나의 제스처 포즈(예: 주먹)를 몇 초간 가만히 유지한 채로 녹화해서
# state_changed(=flicker)가 threshold별로 몇 번 나오는지 비교
# ---------------------------------------------------------
MIN_HAND_DETECTION_CONFIDENCE = 0.8
MIN_HAND_PRESENCE_CONFIDENCE = 0.8
MIN_TRACKING_CONFIDENCE = 0.8

LOG_PATH = f"confidence_log_det{MIN_HAND_DETECTION_CONFIDENCE}_pres{MIN_HAND_PRESENCE_CONFIDENCE}_track{MIN_TRACKING_CONFIDENCE}.csv"

# 웹캠 실시간 테스트: 0
# 저장된 영상으로 세 threshold를 똑같은 입력에 대해 비교하고 싶으면 파일 경로 문자열로 변경
# 예: VIDEO_SOURCE = "gesture_test_clip.mp4"
VIDEO_SOURCE = "confidence_experiment3.mp4"
# ---------------------------------------------------------

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
            annotated_image, f"{handedness[0].category_name} ({handedness[0].score:.2f})",
            (text_x, text_y), cv2.FONT_HERSHEY_DUPLEX,
            FONT_SIZE, HANDEDNESS_TEXT_COLOR, FONT_THICKNESS, cv2.LINE_AA,
        )

    overlay_text = (
        f"det={MIN_HAND_DETECTION_CONFIDENCE} "
        f"pres={MIN_HAND_PRESENCE_CONFIDENCE} "
        f"track={MIN_TRACKING_CONFIDENCE}"
    )
    cv2.putText(
        annotated_image, overlay_text, (10, 30),
        cv2.FONT_HERSHEY_DUPLEX, 0.7, THRESHOLD_TEXT_COLOR, 1, cv2.LINE_AA,
    )
    return annotated_image


def log_frame(csv_writer, frame_idx, timestamp_ms, detection_result, prev_states):
    """한 프레임을 CSV에 기록. 반환값은 (다음 프레임과 비교할 현재 states, 이번 프레임의 gesture_result).
    손을 놓친 프레임이면 (None, None)을 반환해서 flicker 비교가 끊기게 함."""
    hand_world_landmarks_list = detection_result.hand_world_landmarks

    if len(hand_world_landmarks_list) == 0:
        csv_writer.writerow([frame_idx, timestamp_ms, 0] + [""] * (len(FINGER_ORDER) * 2 + 3))
        return None, None, None, None

    ratios = get_finger_ratios(hand_world_landmarks_list[0])
    states = get_finger_states(ratios)
    gesture_result = classify_gesture(states)

    state_changed = int(prev_states is not None and states != prev_states)

    handedness_list = detection_result.handedness
    handedness_score = handedness_list[0][0].score if len(handedness_list) > 0 else ""

    row = [frame_idx, timestamp_ms, 1]
    row += [f"{ratios[f]:.4f}" for f in FINGER_ORDER]
    row += [int(states[f]) for f in FINGER_ORDER]
    row.append(state_changed)
    row.append(gesture_result)
    row.append(f"{handedness_score:.4f}" if handedness_score != "" else "")
    csv_writer.writerow(row)

    return states, gesture_result, ratios, handedness_score


base_options = python.BaseOptions(model_asset_path="../hand_landmarker.task")
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=2,
    running_mode=vision.RunningMode.VIDEO,
    min_hand_detection_confidence=MIN_HAND_DETECTION_CONFIDENCE,
    min_hand_presence_confidence=MIN_HAND_PRESENCE_CONFIDENCE,
    min_tracking_confidence=MIN_TRACKING_CONFIDENCE,
)
detector = vision.HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(VIDEO_SOURCE)
is_file_input = VIDEO_SOURCE != 0

if is_file_input:
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    if not video_fps or video_fps <= 0:
        video_fps = 30.0  # fps 정보를 못 읽어오면 기본값
    print(f"영상 파일 입력: {VIDEO_SOURCE} (fps={video_fps:.2f}) — 프레임 번호 기준으로 타임스탬프 계산")
else:
    start_time = time.time()
frame_idx = 0
prev_states = None
detected_frame_count = 0
gesture_counts = {"ON": 0, "OFF": 0, "알 수 없음": 0}
ratio_history = {f: [] for f in FINGER_ORDER}  # 세션 동안 손가락별 ratio 값 누적 (jitter 계산용)
handedness_score_history = []  # 영상이 threshold를 시험할 만큼 어려운지 확인용

if not cap.isOpened():
    print("입력 소스를 열 수 없습니다.")
else:
    if is_file_input:
        print("영상 파일 열림. 끝까지 자동 재생됩니다 (중간에 멈추려면 'q').")
    else:
        print("웹캠 연결 성공! 'q'를 누르면 종료됩니다.")
    print(f"로그 저장 위치: {LOG_PATH}")

with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
    csv_writer = csv.writer(f)
    csv_writer.writerow(
        ["frame_idx", "timestamp_ms", "hand_detected"]
        + [f"{f}_ratio" for f in FINGER_ORDER]
        + [f"{f}_state" for f in FINGER_ORDER]
        + ["state_changed", "gesture_result", "handedness_score"]
    )

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            if is_file_input:
                print("영상 끝까지 처리 완료.")
            else:
                print("웹캠에서 프레임을 읽을 수 없습니다.")
            break

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        if is_file_input:
            timestamp_ms = int(frame_idx * (1000 / video_fps))
        else:
            timestamp_ms = int((time.time() - start_time) * 1000)

        detection_result = detector.detect_for_video(mp_image, timestamp_ms)

        new_states, gesture_result, ratios, handedness_score = log_frame(csv_writer, frame_idx, timestamp_ms, detection_result, prev_states)
        if new_states is not None:
            detected_frame_count += 1
            gesture_counts[gesture_result] += 1
            for f in FINGER_ORDER:
                ratio_history[f].append(ratios[f])
            handedness_score_history.append(handedness_score)
        prev_states = new_states
        frame_idx += 1

        annotated_image = draw_landmarks_on_image(rgb_frame, detection_result)
        cv2.imshow("Confidence Experiment", cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR))

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
print(f"총 {frame_idx} 프레임 처리 ({detected_frame_count}프레임에서 손 감지)")
if detected_frame_count > 0:
    for label, count in gesture_counts.items():
        pct = count / detected_frame_count * 100
        print(f"  {label}: {count}프레임 ({pct:.1f}%)")
    print("  -> 같은 포즈를 계속 유지했다면 '알 수 없음' 비율이 곧 이 threshold의 오작동 위험도")

if handedness_score_history:
    print(f"handedness_score 범위: min={min(handedness_score_history):.4f}, max={max(handedness_score_history):.4f}, avg={np.mean(handedness_score_history):.4f}")

print("손가락별 ratio jitter:")
for f in FINGER_ORDER:
    values = ratio_history[f]
    if len(values) > 1:
        print(f"  {f}: std={np.std(values):.4f}, range={max(values) - min(values):.4f}")
print(f"로그는 {LOG_PATH}에 저장됨")