import json
import os
import sys
from pynput import mouse
from termcolor import colored
from playsound import playsound

aimbot_enabled = True

def on_click(x, y, button, pressed):
    global aimbot_enabled
    if pressed:
        if button == mouse.Button.button9:  # Button9 for toggle (usually Mouse Button 5)
            aimbot_enabled = not aimbot_enabled
            if aimbot_enabled:
                print(colored('[AIMBOT ENABLED]', 'green'))
                try:
                    playsound('lib/aim_on.wav', block=False)
                except:
                    pass
            else:
                print(colored('[AIMBOT DISABLED]', 'red'))
                try:
                    playsound('lib/aim_off.wav', block=False)
                except:
                    pass
        elif button == mouse.Button.button8:  # Button8 for exit (usually Mouse Button 4)
            print(colored('[AIMBOT EXIT]', 'yellow'))
            os._exit(0)


def main():
    global lunar
    from lib.aimbot import Aimbot
    lunar = Aimbot(collect_data = "collect_data" in sys.argv)
    lunar.start(lambda: aimbot_enabled)

def setup():
    path = "lib/config"
    if not os.path.exists(path):
        os.makedirs(path)

    print("[INFO] In-game X and Y axis sensitivity should be the same")
    def prompt(str):
        valid_input = False
        while not valid_input:
            try:
                number = float(input(str))
                valid_input = True
            except ValueError:
                print("[!] Invalid Input. Make sure to enter only the number (e.g. 6.9)")
        return number

    xy_sens = prompt("X-Axis and Y-Axis Sensitivity (from in-game settings): ")
    targeting_sens = prompt("Targeting Sensitivity (from in-game settings): ")

    print("[INFO] Your in-game targeting sensitivity must be the same as your scoping sensitivity")
    sensitivity_settings = {"xy_sens": xy_sens, "targeting_sens": targeting_sens, "xy_scale": 10/xy_sens, "targeting_scale": 1000/(targeting_sens * xy_sens)}

    with open('lib/config/config.json', 'w') as outfile:
        json.dump(sensitivity_settings, outfile)
    print("[INFO] Sensitivity configuration complete")

if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

    print(colored('''

  _    _   _ _   _    _    ____     _     ___ _____ _____ 
 | |  | | | | \ | |  / \  |  _ \   | |   |_ _|_   _| ____|
 | |  | | | |  \| | / _ \ | |_| |  | |    | |  | | |  _|  
 | |__| |_| | |\  |/ ___ \|  _ <   | |___ | |  | | | |___ 
 |_____\___/|_| \_/_/   \_\_| \_\  |_____|___| |_| |_____|
                                                                         
(Neural Network Aimbot)''', "green"))
    
    print(colored('To get full version of Lunar V2, visit https://gannonr.com/lunar OR join the discord: discord.gg/aiaimbot', "red"))

    path_exists = os.path.exists("lib/config/config.json")
    if not path_exists or ("setup" in sys.argv):
        if not path_exists:
            print("[!] Sensitivity configuration is not set")
        setup()
    path_exists = os.path.exists("lib/data")
    if "collect_data" in sys.argv and not path_exists:
        os.makedirs("lib/data")
    mouse_listener = mouse.Listener(on_click=on_click)
    mouse_listener.start()
    main()
