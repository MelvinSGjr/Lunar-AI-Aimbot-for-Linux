import ctypes
import cv2
import json
import math
import mss
import os
import sys
import time
import torch
import numpy as np
from termcolor import colored
from ultralytics import YOLO
import platform
import subprocess
try:
    import pyautogui
except ImportError:
    pyautogui = None

# If you're a skid and you know it clap your hands 👏👏

# Auto Screen Resolution
if platform.system() == 'Windows':
    screensize = {'X': ctypes.windll.user32.GetSystemMetrics(0), 'Y': ctypes.windll.user32.GetSystemMetrics(1)}
else:
    if pyautogui:
        screensize = {'X': pyautogui.size().width, 'Y': pyautogui.size().height}
    else:
        screensize = {'X': 1920, 'Y': 1080}  # fallback

# If you use stretched res, hardcode the X and Y. For example: screen_res_x = 1234
screen_res_x = screensize['X']
screen_res_y = screensize['Y']

# Divide screen_res by 2
# No need to change this
screen_x = int(screen_res_x / 2)
screen_y = int(screen_res_y / 2)

aim_height = 10 # The lower the number, the higher the aim_height. For example: 2 would be the head and 100 would be the feet.

fov = 350

confidence = 0.45 # How confident the AI needs to be for it to lock on to the player. Default is 45%

use_trigger_bot = False # Will shoot if crosshair is locked on the player

# Removed mouse_methods, mouse_dll, and all ddxoft checks

PUL = ctypes.POINTER(ctypes.c_ulong)
class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_ushort)]

class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput),
                ("mi", MouseInput),
                ("hi", HardwareInput)]

class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("ii", Input_I)]

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class Aimbot:
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    screen = mss.mss()
    pixel_increment = 1 #controls how many pixels the mouse moves for each relative movement
    with open("lib/config/config.json") as f:
        sens_config = json.load(f)
    aimbot_status = colored("ENABLED", 'green')

    def __init__(self, box_constant = fov, collect_data = False, mouse_delay = 0.0009):
        #controls the initial centered box width and height of the "Lunar Vision" window
        self.box_constant = box_constant #controls the size of the detection box (equaling the width and height)

        print("[INFO] Loading the neural network model")
        self.model = YOLO('lib/best.pt')
        if torch.cuda.is_available():
            print(colored("CUDA ACCELERATION [ENABLED]", "green"))
        else:
            print(colored("[!] CUDA ACCELERATION IS UNAVAILABLE", "red"))
            print(colored("[!] Check your PyTorch installation, else performance will be poor", "red"))

        self.conf = confidence # base confidence threshold (or base detection (0-1)
        self.iou = 0.45 # NMS IoU (0-1)
        self.collect_data = collect_data
        self.mouse_delay = mouse_delay

        print("\n[INFO] PRESS 'F1' TO TOGGLE AIMBOT\n[INFO] PRESS 'F2' TO QUIT")

    def update_status_aimbot():
        if Aimbot.aimbot_status == colored("ENABLED", 'green'):
            Aimbot.aimbot_status = colored("DISABLED", 'red')
        else:
            Aimbot.aimbot_status = colored("ENABLED", 'green')
        sys.stdout.write("\033[K")
        print(f"[!] AIMBOT IS [{Aimbot.aimbot_status}]", end = "\r")

    def left_click(self):
        if platform.system() == 'Windows':
            ctypes.windll.user32.mouse_event(0x0002)
            Aimbot.sleep(0.0001)
            ctypes.windll.user32.mouse_event(0x0004)
        else:
            if pyautogui:
                pyautogui.mouseDown()
                Aimbot.sleep(0.001)
                pyautogui.mouseUp()

    def sleep(duration, get_now = time.perf_counter):
        if duration == 0: return
        now = get_now()
        end = now + duration
        while now < end:
            now = get_now()

    def is_aimbot_enabled():
        return Aimbot.aimbot_status == colored("ENABLED", 'green')

    def is_shooting():
        if pyautogui:
            return pyautogui.mouseDown()
        return False

    def is_targeted():
        return False  # Not implemented for Linux

    def is_target_locked(x, y):
        #plus/minus 5 pixel threshold
        threshold = 5
        return screen_x - threshold <= x <= screen_x + threshold and screen_y - threshold <= y <= screen_y + threshold

    def move_mouse_xdotool(self, dx, dy):
        try:
            subprocess.run(["xdotool", "mousemove_relative", "--", str(int(dx)), str(int(dy))], check=True)
        except Exception as e:
            print(f"[AIMBOT] xdotool error: {e}")

    def move_crosshair(self, x, y):
        if platform.system() == 'Windows':
            if Aimbot.is_targeted():
                scale = Aimbot.sens_config["targeting_scale"]
            else:
                return
            for rel_x, rel_y in Aimbot.interpolate_coordinates_from_center((x, y), scale):
                Aimbot.ii_.mi = MouseInput(rel_x, rel_y, 0, 0x0001, 0, ctypes.pointer(Aimbot.extra))
                input_obj = Input(ctypes.c_ulong(0), Aimbot.ii_)
                ctypes.windll.user32.SendInput(1, ctypes.byref(input_obj), ctypes.sizeof(input_obj))
                Aimbot.sleep(self.mouse_delay)
        else:
            # Move mouse a small step towards the target each frame (relative to screen center) using xdotool
            center_x = screen_x
            center_y = screen_y
            dx = x - center_x
            dy = y - center_y
            scale = 1.96  # Increase for faster movement
            move_x = dx * scale
            move_y = dy * scale  # No inversion for xdotool in most games
            max_step = 135  # Increase for faster movement
            move_x = max(-max_step, min(max_step, move_x))
            move_y = max(-max_step, min(max_step, move_y))
            # Only move if distance is significant
            if abs(move_x) > 1 or abs(move_y) > 1:
                self.move_mouse_xdotool(move_x, move_y)
            Aimbot.sleep(self.mouse_delay)

    #generator yields pixel tuples for relative movement
    def interpolate_coordinates_from_center(absolute_coordinates, scale):
        diff_x = (absolute_coordinates[0] - screen_x) * scale/Aimbot.pixel_increment
        diff_y = (absolute_coordinates[1] - screen_y) * scale/Aimbot.pixel_increment
        length = int(math.dist((0,0), (diff_x, diff_y)))
        if length == 0: return
        unit_x = (diff_x/length) * Aimbot.pixel_increment
        unit_y = (diff_y/length) * Aimbot.pixel_increment
        x = y = sum_x = sum_y = 0
        for k in range(0, length):
            sum_x += x
            sum_y += y
            x, y = round(unit_x * k - sum_x), round(unit_y * k - sum_y)
            yield x, y
            

    def start(self, is_aimbot_enabled_fn=None):
        print("[INFO] Beginning screen capture")
        if platform.system() == 'Windows':
            half_screen_width = ctypes.windll.user32.GetSystemMetrics(0)/2
            half_screen_height = ctypes.windll.user32.GetSystemMetrics(1)/2
        else:
            half_screen_width = screensize['X']/2
            half_screen_height = screensize['Y']/2
        detection_box = {'left': int(half_screen_width - self.box_constant//2),
                          'top': int(half_screen_height - self.box_constant//2),
                          'width': int(self.box_constant),
                          'height': int(self.box_constant)}

        while True:
            if is_aimbot_enabled_fn and not is_aimbot_enabled_fn():
                time.sleep(0.01)
                continue
            start_time = time.perf_counter()
            initial_frame = Aimbot.screen.grab(detection_box)
            frame = np.array(initial_frame, dtype=np.uint8)
            if frame is None or frame.size == 0:
                continue
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            boxes = self.model.predict(source=frame, verbose=False, conf=self.conf, iou=self.iou, half=True)
            result = boxes[0]
            if len(result.boxes.xyxy) != 0: #player detected
                least_crosshair_dist = closest_detection = player_in_frame = False
                for box in result.boxes.xyxy: #iterate over each player detected
                    x1, y1, x2, y2 = map(int, box)
                    x1y1 = (x1, y1)
                    x2y2 = (x2, y2)
                    height = y2 - y1
                    relative_head_X, relative_head_Y = int((x1 + x2)/2), int((y1 + y2)/2 - height/aim_height) # offset to roughly approximate the head using a ratio of the height
                    own_player = x1 < 15 or (x1 < self.box_constant/5 and y2 > self.box_constant/1.2) # helps ensure that your own player is not regarded as a valid detection

                    #calculate the distance between each detection and the crosshair at (self.box_constant/2, self.box_constant/2)
                    crosshair_dist = math.dist((relative_head_X, relative_head_Y), (self.box_constant/2, self.box_constant/2))

                    if not least_crosshair_dist: least_crosshair_dist = crosshair_dist #initalize least crosshair distance variable first iteration

                    if crosshair_dist <= least_crosshair_dist and not own_player:
                        least_crosshair_dist = crosshair_dist
                        closest_detection = {"x1y1": x1y1, "x2y2": x2y2, "relative_head_X": relative_head_X, "relative_head_Y": relative_head_Y}

                    if own_player:
                        own_player = False
                        if not player_in_frame:
                            player_in_frame = True

                if closest_detection: #if valid detection exists
                    cv2.circle(frame, (closest_detection["relative_head_X"], closest_detection["relative_head_Y"]), 5, (115, 244, 113), -1) #draw circle on the head

                    #draw line from the crosshair to the head
                    cv2.line(frame, (closest_detection["relative_head_X"], closest_detection["relative_head_Y"]), (self.box_constant//2, self.box_constant//2), (244, 242, 113), 2)

                    absolute_head_X, absolute_head_Y = closest_detection["relative_head_X"] + detection_box['left'], closest_detection["relative_head_Y"] + detection_box['top']
                    x1, y1 = closest_detection["x1y1"]

                    if Aimbot.is_target_locked(absolute_head_X, absolute_head_Y):
                        if use_trigger_bot and not Aimbot.is_shooting():
                            self.left_click()

                        cv2.putText(frame, "LOCKED", (x1 + 40, y1), cv2.FONT_HERSHEY_DUPLEX, 0.5, (115, 244, 113), 2) #draw the confidence labels on the bounding boxes
                    else:
                        cv2.putText(frame, "TARGETING", (x1 + 40, y1), cv2.FONT_HERSHEY_DUPLEX, 0.5, (115, 113, 244), 2) #draw the confidence labels on the bounding boxes

                    # Only move if target is not in the center (distance > 5 pixels)
                    if Aimbot.is_aimbot_enabled() and math.dist((absolute_head_X, absolute_head_Y), (screen_x, screen_y)) > 5:
                        Aimbot.move_crosshair(self, absolute_head_X, absolute_head_Y)

            cv2.putText(frame, f"FPS: {int(1/(time.perf_counter() - start_time))}", (5, 30), cv2.FONT_HERSHEY_DUPLEX, 1, (113, 116, 244), 2)
            cv2.imshow("Screen Capture", frame)
            if cv2.waitKey(1) & 0xFF == ord('0'):
                break

    def clean_up():
        print("\n[INFO] F2 WAS PRESSED. QUITTING...")
        Aimbot.screen.close()
        os._exit(0)

if __name__ == "__main__": print("You are in the wrong directory and are running the wrong file; you must run lunar.py")
