import threading
import time
import platform
import pyautogui
import tkinter as tk
import subprocess
from tkinter import ttk
from tkinter import messagebox
import pyperclip

#from pynput import mouse, keyboard
ctrl = 'command' if platform.system() == 'Darwin' else 'ctrl'
print('Using modifier:', ctrl)  # sanity check in console

class Macro:
    def __init__(self, root:tk.Tk):
        self.root = root
        self.root.title("Macro Controller")
        self._build_ui()
        self.Xpos = None
        self.Ypos = None

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        #self.startXY = pyautogui.center('LocateImage.png')
        self.startXY = None
        self.textEdit = None

        #Settings
        self.newNote_Y = 55
        self.startCoords = self.locateNoteStart()
        self.noteX = self.startCoords[0]
        self.noteY = self.startCoords[1]
        self.textEdit = self.locateTextEditStart()
        self.stopMacro = False
        self.newNote = True
        self.before = None

        
    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}
        live_frame = ttk.LabelFrame(self.root, text="Macro Controller")
        live_frame.grid(row=0, column=0, sticky="nsew", **pad)
        ttk.Button(live_frame, text="Start Macro", command=self._begin_macro_).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6,0))
        ttk.Button(live_frame, text="Stop Macro", command=self._stop_macro_).grid(row=1, column=2, columnspan=2, sticky="ew", pady=(6,0))


    def mac_cmd(self, char: str):
        # send Command+<char> via System Events (bypasses PyAutoGUI timing/modifier issues)
        subprocess.run(["osascript", "-e",
            f'tell application "System Events" to keystroke "{char}" using {{command down}}'])

    def mac_menu(self, app_name: str, menu: str, item: str):
        # optional: invoke exact menu item instead of keystroke
        script = f'''
        tell application "{app_name}" to activate
        tell application "System Events"
            click menu item "{item}" of menu "{menu}" of menu bar 1 of process "{app_name}"
        end tell'''
        subprocess.run(["osascript","-e", script])

#-----------------------------------------------------------------------------------------
    def _begin_macro_(self):
        start = True
        while self.newNote:
            if (self.stopMacro):
                print("Stopping Macro")
                break
            if(start):
                pyautogui.click(self.noteX, self.noteY)
                start = False
            else:
                pyautogui.doubleClick(240, 100)     # focus the note list                   # tiny settle
                time.sleep(0.05)
                pyautogui.press('down')          
                time.sleep(0.05)    # go to next note (not hotkey)
            self.noteX += 200
            pyautogui.click(750,95) #Click on Note Data
            time.sleep(0.05)
            self.before = pyperclip.paste()
            time.sleep(0.05)
            self.mac_cmd('a'); time.sleep(0.05)  # or: mac_menu("Notes","Edit","Select All")
            self.mac_cmd('c'); time.sleep(0.05) 
            if not (self.newNoteCheck()):
                break
            pyautogui.click(self.textEdit)
            pyautogui.write('"""') 
            pyautogui.press('enter')
            self.mac_cmd('v')  
            pyautogui.press('enter')
            pyautogui.write('"""') 
            pyautogui.press('enter')
            self.noteX -= 200

        self.noteX = (self.locateNoteStart())[0]
        self.noteY = (self.locateNoteStart())[1]

#-----------------------------------------------------------------------------------------
    def newNoteCheck(self):
        self.after = pyperclip.paste()
        if self.before == self.after:
            newNote = False
            return False
        else: return True

    def _stop_macro_(self):
        self.stopMacro = True

    def locateNoteStart(self):
        #self.startXY = pyautogui.center('LocateImage.png')
        if self.startXY == None:
            print("Locating Image Not Found")
        else:
            print("Start intialized at X: " + str(self.startXY[0]) + " Y: " + str(self.startXY[1]))
        return (240,170)

    def locateTextEditStart(self):
        return (850,50)

    def _on_close(self):
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    # Use ttk theme for consistency
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except Exception:
        pass
    app = Macro(root)
    root.mainloop()
