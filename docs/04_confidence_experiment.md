# Confidence Threshold 실험

## 목적

MediaPipe HandLandmarker의 세 가지 confidence 파라미터(`min_hand_detection_confidence`,
`min_hand_presence_confidence`, `min_tracking_confidence`)가 ON/OFF 제스처 인식의
안정성(landmark jitter, 오판정 빈도)에 실제로 영향을 주는지 확인한다.

- ON: 손가락 5개 전부 펴짐
- OFF: 손가락 5개 전부 굽힘
- 판정(`classify_gesture`)은 5개 손가락 상태가 정확히 일치해야만 ON/OFF로 인식되고,
  하나라도 어긋나면 "알 수 없음"으로 분류됨 → 그만큼 landmark 노이즈에 민감한 구조

## 실험 방법

- `src/confidence_experiment.py` 작성
  - `running_mode=VIDEO`로 웹캠 또는 저장된 영상 파일(`VIDEO_SOURCE`)을 프레임 단위로 처리
  - `finger_state.py`(`get_finger_ratios`, `get_finger_states`), `gesture.py`(`classify_gesture`) 재사용
  - 매 프레임 CSV 로깅: 손가락별 ratio/state, `gesture_result`, `state_changed`, `handedness_score`
  - 세션 종료 시 콘솔에 감지율, ON/OFF/알 수 없음 비율, `handedness_score` 범위, 손가락별 jitter(std/range) 요약 출력
- 같은 영상을 재사용해 threshold 값(낮음 0.3 / 기본 0.5 / 높음 0.8)만 바꿔가며 비교
  → 손 위치·거리·타이밍 등 다른 변수를 통제해 공정하게 비교
- 영상 파일 입력 시 타임스탬프는 실제 fps 기준(`frame_idx × 1000/fps`)으로 계산 (webcam의 실시간 타임스탬프와 구분)

## 실험 1: 첫 촬영 영상 (조건이 너무 쉬웠음)

정면에서 촬영한 ON/OFF 자세, 밝은 조명, 단순 배경(천장), 가까운 거리.

- `handedness_score`가 항상 0.90~1.0 사이 → 테스트한 threshold(0.3~0.8) 범위를 항상 크게 상회
- 결과: threshold를 0.3/0.5/0.8 어느 값으로 바꿔도 flip 횟수, ON/OFF 비율, jitter(std)까지
  소수점 단위로 완전히 동일
- **결론**: 좋은 촬영 조건(정면, 밝음, 단순 배경)에서는 confidence threshold가 결과에
  영향을 주지 않는다 — 모델이 내는 실제 confidence 점수가 항상 threshold를 여유 있게
  넘기 때문. 이 조건만으로는 threshold 비교 실험이 성립하지 않음을 확인.

## 실험 2: 회전 자세 추가 (confidence_experiment2.mp4)

정면 주먹 → 손목을 옆으로 크게 돌려 유지 → 유지한 채로 흔들기, 순서로 촬영.

프레임 단위 분석 결과 (threshold 0.5 기준):

| 구간 | 시간 | gesture_result 패턴 |
|---|---|---|
| 정면 주먹 | 0~2.9초 | OFF로 안정적 |
| 회전 유지 | 2.9~7.1초 (약 4.2초) | **한 번도 안 끊기고 계속 "알 수 없음"** |
| 흔들기 | 7.1초~ | OFF ↔ 알 수 없음이 수십~수백 ms 단위로 빠르게 반복 (모션 블러 패턴) |

- 회전 구간은 threshold(0.3/0.5/0.8)를 바꿔도 거의 동일하게 실패 (차이는 흔들기 구간에서 3프레임 정도만)
- **결론**: 손목 회전 각도가 크면 confidence threshold와 무관하게 인식이 실패한다.
  손가락끼리 서로 가려지며 landmark 3D 위치 추정 자체가 부정확해지는 것으로 추정됨.
  이건 confidence 튜닝으로 해결할 수 있는 문제가 아니라 **손 각도에 대한 제약 조건**으로
  다뤄야 함 (아래 "후속 이슈" 참고).

## 실험 3: 회전 제외, 정면 + 흔들기만 (confidence_experiment3.mp4)

실험 2에서 회전과 흔들기 두 원인이 섞여 있었기 때문에, 회전을 빼고 정면 자세를 유지한 채
흔들기만 다시 촬영해서 순수하게 모션 블러/추적 안정성만 테스트.

| threshold | 감지율 (전체 186프레임 중) | OFF / 알 수 없음 (감지된 프레임 중) | handedness_score 범위 |
|---|---|---|---|
| 0.3 | 168/186 (90.3%) | 73.2% / 26.8% | min 0.5733, max 0.9978 |
| 0.5 | 170/186 (91.4%) ← 최고 | 74.7% / 25.3% | min 0.5117, max 0.9978 |
| 0.8 | 162/186 (87.1%) ← 최저 | 74.7% / 25.3% | min 0.5109, max 0.9977 |

손가락별 ratio jitter(std) — threshold가 높을수록 거의 모든 손가락에서 꾸준히 감소:

| 손가락 | 0.3 | 0.5 | 0.8 |
|---|---|---|---|
| 엄지 | 0.2863 | 0.2662 | 0.2475 |
| 검지 | 0.0804 | 0.0753 | 0.0589 |
| 중지 | 0.0967 | 0.0913 | 0.0611 |
| 약지 | 0.1116 | 0.1092 | 0.0693 |
| 소지 | 0.1081 | 0.1101 | 0.0701 |

**결론**:
- threshold가 높을수록 통과된 프레임의 landmark는 더 안정적(jitter 감소)
- 대신 손을 아예 놓치는 프레임은 늘어남 (0.8이 감지율 최저) → 안정성과 감지율의 trade-off
- OFF vs 알 수 없음 비율 자체는 threshold와 거의 무관 (73~75%대로 유지) — 모션 블러로 인한
  오판정은 threshold로 근본적으로 없앨 수 없음
- 이번 테스트에서는 0.5가 감지율(91.4%, 최고)과 jitter 사이에서 무난한 균형점

## 최종 결론

1. **confidence threshold는 기본값(0.5)을 그대로 사용**하는 것이 합리적. 조용한 환경에서는
   threshold가 결과에 거의 영향이 없고, 빠른 움직임이 섞인 어려운 조건에서도 0.5가 감지율과
   안정성 사이 균형이 가장 좋았음.
2. **손 각도 제약**: 손목을 많이 회전하면 threshold와 무관하게 인식이 실패함. 실사용 시
   손이 카메라를 어느 정도 정면으로 향하는 각도 범위 내에서만 안정적으로 동작한다고
   가정해야 함.
3. **모션 블러 대응**: 빠른 손 움직임으로 인한 순간적인 오판정은 confidence 튜닝으로
   완전히 없어지지 않음. 실제 제스처 로직에서는 포즈를 일정 프레임 이상 연속으로 유지해야
   인정하는 디바운스(debounce) 처리를 추가하면, 이런 찰나의 오판정이 자연스럽게 걸러질 것으로
   예상됨 (아직 미구현).

## 후속 이슈 (다음에 다룰 것)

- 손 각도 허용 범위를 정량적으로 측정 (몇 도부터 인식이 깨지기 시작하는지 단계별 촬영 필요)
- 디바운스(포즈 유지 프레임 수 기준 판정) 로직을 `gesture.py`에 추가하는 것 검토

## 사용한 파일

- `src/confidence_experiment.py`
- 테스트 영상: 초기 촬영본(조건 쉬움) / `confidence_experiment2.mp4`(회전+흔들기) /
  `confidence_experiment3.mp4`(정면+흔들기)
- CSV 로그: 영상별 × threshold(0.3/0.5/0.8) 조합으로 총 9개