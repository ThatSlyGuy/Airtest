import subprocess
from shutil import copy
from win32com.client import GetObject
from win32api import GetSystemMetrics
import os
from time import sleep
from pathlib import Path
from math import floor

class WindowsRecorder():

    def __init__(self, recordingWindow):
        self.recordingWindow = recordingWindow
        self.defaultOutputDirectory = 'temp_recording.mp4'

    def start_recording(self, max_time=7200):
        try:
            rect = self.recordingWindow.rectangle()
            winOrigin = [rect.left, rect.top]
            width = rect.width()
            height = rect.height()            
        except:
            winOrigin = [0, 0]
            width = GetSystemMetrics(0)
            height = GetSystemMetrics(1)
        
        width = floor(width / 2) * 2
        height = floor(height / 2) * 2
        winResolution = '{0}x{1}'.format(width, height)
        command = 'ffmpeg -y -rtbufsize 100M -f gdigrab -offset_x {0} -offset_y {1} -video_size {2} -t {3} -framerate 20 -probesize 10M -draw_mouse 1 -i desktop -c:v libx264 -r 30 -preset ultrafast -tune zerolatency -crf 25 -pix_fmt yuv420p {4}'.format(winOrigin[0], winOrigin[1], winResolution, max_time, self.defaultOutputDirectory)
        print('\n----> Recording command: ', flush=True)
        print(command, flush=True)
        subprocess.Popen('start /MIN cmd.exe /c {0}'.format(command), shell=True)

        return True
        
    def stop_recording(self, output="screen.mp4", is_interrupted=False):
        try:
            WMI = GetObject('winmgmts:')

            for p in WMI.ExecQuery('select * from Win32_Process where Name="cmd.exe"'):
                os.system('taskkill /pid ' + str(p.Properties_('ProcessId').Value))
        except:
            pass

        sleep(1)
        copy(self.defaultOutputDirectory, output)