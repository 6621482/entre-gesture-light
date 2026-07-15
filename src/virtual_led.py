"""
virtual_led.py - 가상 조명 시뮬레이터

실제 하드웨어 없이 제스처 인식 -> 조명 제어 로직을 먼저 테스트하기 위한 모듈 
ON/OFF + 밝기 조절만 하므로, LED마다 켜짐/꺼짐 + 밝기 두 값만 관리함 
"""

import threading
import tkinter as tk

class VirtualLight:
    def __init__(self):
        self.is_on = False  # 처음엔 꺼진 상태로 시작
        self.brightness = 50  # 밝기 기본값 50% 

    def turn_on(self):
        self.is_on = True
    
    def turn_off(self):
        self.is_on = False
    
    def set_brightness(self, value):
        self.brightness = max(0, min(100, value))

# VirtualLight의 현재 상태를 계속 읽어서 화면에 그려주는 창
# gesture.demo.py의 웹캠 루프와 동시에 돌아가야 하므로 별도 스레드로 실행
class LEDVisualizer(threading.Thread):
    def __init__(self, light: VirtualLight, n_pixels=30, refresh_ms=50):
        super().__init__(daemon=True)   # daemon=True: 메인 프로그램이 끝나면 창도 같이 닫힘
        self.light = light
        self.n_pixels = n_pixels
        self.refresh_ms = refresh_ms

    def run(self):
        self.root = tk.Tk()
        self.root.title("Virtual LED Strip")
        self.root.configure(bg="#111111")

        size, pad = 30, 15
        width = self.n_pixels * (size + pad) + pad
        self.canvas = tk.Canvas(self.root, width=width, height=size+2*pad, bg="#111111", highlightthickness=0)
        self.canvas.pack()

        # LED 개수만큼 동그라미를 미리 그려두고, 나중엔 색만 바꿔서 재사용
        self.ovals = []
        for i in range(self.n_pixels):
            x0 = pad + i * (size + pad)
            oval = self.canvas.create_oval(x0, pad, x0 + size, pad + size,
                                            fill="#222222", outline="#444444")
            self.ovals.append(oval)

        self._tick()          # 첫 갱신 실행
        self.root.mainloop()  # 창을 계속 띄워둠

    def _tick(self):
        # 0.05초(refresh_ms)마다 반복 호출되면서 현재 상태를 화면에 반영
        color = self._current_color()
        for oval in self.ovals:
            self.canvas.itemconfig(oval, fill=color)
        self.root.after(self.refresh_ms, self._tick)  # 스스로를 다시 예약

    def _current_color(self):
        if not self.light.is_on:
            return "#222222"  # 꺼짐: 어두운 회색
        v = int(255 * self.light.brightness / 100)
        return f"#{v:02x}{v:02x}{v:02x}"  # 켜짐: 밝기만큼 밝은 흰색
