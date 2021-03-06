#! /usr/bin/env python
# -*- coding: utf-8 -*-


import requests
import six
import time
import json
import base64
import wda
import traceback
from urllib.request import urlopen
from json import loads
from os import path
from subprocess import Popen

if six.PY3:
    from urllib.parse import urljoin
else:
    from urlparse import urljoin

from airtest import aircv
from airtest.core.device import Device
from airtest.core.ios.constant import CAP_METHOD, TOUCH_METHOD, IME_METHOD
from airtest.core.ios.rotation import XYTransformer, RotationWatcher
from airtest.core.ios.fake_minitouch import fakeMiniTouch
from airtest.core.ios.instruct_helper import InstructHelper
from airtest.core.ios.idb import IDB
from airtest.utils.logger import get_logger

# roatations of ios
from wda import LANDSCAPE, PORTRAIT, LANDSCAPE_RIGHT, PORTRAIT_UPSIDEDOWN
from wda import WDAError


logger = get_logger(__name__)
DEFAULT_ADDR = "http://localhost:8100/"

# retry when saved session failed
def retry_session(func):
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except WDAError as err:
            # 6 : Session does not exist
            if err.status == 6:
                self._fetchNewSession()
                return func(self, *args, **kwargs)
            else:
                raise err
    return wrapper

class IOS(Device):
    """ios client

        - before this you have to run `WebDriverAgent <https://github.com/AirtestProject/iOS-Tagent>`_

        - ``xcodebuild -project path/to/WebDriverAgent.xcodeproj -scheme WebDriverAgentRunner -destination "id=$(idevice_id -l)" test``

        - ``iproxy $port 8100 $udid``
    """

    def __init__(self, addr=DEFAULT_ADDR, udid=None):
        super(IOS, self).__init__()

        # if none or empty, use default addr
        self.addr = addr or DEFAULT_ADDR

        # fit wda format, make url start with http://
        if not self.addr.startswith("http://"):
            self.addr = "http://" + addr

        """here now use these supported cap touch and ime method"""
        self.cap_method = CAP_METHOD.WDACAP
        self.touch_method = TOUCH_METHOD.WDATOUCH
        self.ime_method = IME_METHOD.WDAIME

        # wda driver, use to home, start app
        # init wda session, updata when start app
        # use to click/swipe/close app/get wda size
        wda.DEBUG = False
        self.driver = wda.Client(self.addr)

        # record device's width
        self._size = {'width': None, 'height': None}
        self._touch_factor = 0.5
        self._last_orientation = None
        self.defaultSession = None

        # start up RotationWatcher with default session
        self.rotation_watcher = RotationWatcher(self)

        # fake minitouch to simulate swipe
        self.minitouch = fakeMiniTouch(self)

        # helper of run process like iproxy
        self.instruct_helper = InstructHelper()

        if not udid:
            try:
                with urlopen(f'http://{addr}/status') as url:
                    deviceStatus = loads(url.read().decode())['value']
                    udid = deviceStatus['device']['udid']
            except:
                pass

        self.idb = IDB(udid) if udid else None
        self.recordingProcess = None
        self.rotationInGame = 270

    @property
    def uuid(self):
        return self.addr

    @property
    def session(self):
        if not self.defaultSession:
            self.defaultSession = self.driver.session()
        return self.defaultSession

    def _fetchNewSession(self):
        self.defaultSession = self.driver.session()

    @retry_session
    def window_size(self):
        """
            return window size
            namedtuple:
                Size(wide , hight)
        """
        return self.session.window_size()

    @property
    @retry_session
    def orientation(self):
        """
            return device oritantation status
            in  LANDSACPE POR
        """
        return self.session.orientation

    @property
    def display_info(self):
        if not self._size['width'] or not self._size['height']:
            self.snapshot()

        return {'width': self._size['width'], 'height': self._size['height'], 'orientation': self.orientation,\
        'physical_width': self._size['width'], 'physical_height': self._size['height']}

    def get_render_resolution(self):
        """
        Return render resolution after rotation

        Returns:
            offset_x, offset_y, offset_width and offset_height of the display

        """
        w, h = self.get_current_resolution()
        return 0, 0, w, h

    def start_recording(self, *args, **kwargs):
        """
        Start recording the device display

        Args:
            *args: optional arguments
            **kwargs:  optional arguments

        Returns:
            None

        """
        self.recordingProcess = self.idb.start_recording('screen.mp4')

    def stop_recording(self, output="screen.mp4", **kwargs):
        """
        Stop recording the device display. Recoding file will be kept in the device.

        Args:
            output: default file is `screen.mp4`
            **kwargs: optional arguments

        Returns:
            None

        """
        if self.recordingProcess != None:
            self.recordingProcess.kill()

        time.sleep(1)

        if path.isfile(self.idb.recordingPath):
            rotateVideoProcess = Popen(f'ffmpeg -i {self.idb.recordingPath} -vf "transpose={1 if self.rotationInGame == 270 else 2}" {output}', shell=True)
            rotateVideoProcess.wait()

    def get_current_resolution(self):
        w, h = self.display_info["width"], self.display_info["height"]
        if self.display_info["orientation"] in [LANDSCAPE, LANDSCAPE_RIGHT]:
            w, h = h, w
        return w, h

    def home(self):
        return self.driver.home()

    def _neo_wda_screenshot(self):
        """
            this is almost same as wda implementation, but without png header check,
            as response data is now jpg format in mid quality
        """
        value = self.driver.http.get('screenshot').value
        raw_value = base64.b64decode(value)
        return raw_value

    def snapshot(self, filename=None, strType=False, quality=10):
        """
        take snapshot
        filename: save screenshot to filename
        quality: The image quality, integer in range [1, 99]
        """
        data = None

        if self.cap_method == CAP_METHOD.MINICAP:
            raise NotImplementedError
        elif self.cap_method == CAP_METHOD.MINICAP_STREAM:
            raise NotImplementedError
        elif self.cap_method == CAP_METHOD.WDACAP:
            data = self._neo_wda_screenshot()  # wda 截图不用考虑朝向

        # 实时刷新手机画面，直接返回base64格式，旋转问题交给IDE处理
        if strType:
            if filename:
                with open(filename, 'wb') as f:
                    f.write(data)
            return data

        # output cv2 object
        try:
            screen = aircv.utils.string_2_img(data)
        except:
            # may be black/locked screen or other reason, print exc for debugging
            traceback.print_exc()
            return None

        h, w = screen.shape[:2]

        # save last res for portrait
        if self.orientation in [LANDSCAPE, LANDSCAPE_RIGHT]:
            self._size['height'] = w
            self._size['width'] = h
        else:
            self._size['height'] = h
            self._size['width'] = w

        winw, winh = self.window_size()

        self._touch_factor = float(winh) / float(h)

        # save as file if needed
        if filename:
            aircv.imwrite(filename, screen, quality)

        return screen

    @retry_session
    def touch(self, pos, duration=0.01):
        # trans pos of click
        pos = self._touch_point_by_orientation(pos)

        # scale touch postion
        x, y = pos[0] * self._touch_factor, pos[1] * self._touch_factor
        if duration >= 0.5:
            self.session.tap_hold(x, y, duration)
        else:
            self.session.tap(x, y)

    def double_click(self, pos):
        # trans pos of click
        pos = self._touch_point_by_orientation(pos)

        x, y = pos[0] * self._touch_factor, pos[1] * self._touch_factor
        self.session.double_tap(x, y)

    def swipe(self, fpos, tpos, duration=0.5, steps=5, fingers=1):
        # trans pos of swipe
        fx, fy = self._touch_point_by_orientation(fpos)
        tx, ty = self._touch_point_by_orientation(tpos)

        self.session.swipe(fx * self._touch_factor, fy * self._touch_factor,
                           tx * self._touch_factor, ty * self._touch_factor, duration)

    def keyevent(self, keys):
        """just use as home event"""
        if keys not in ['HOME', 'home', 'Home']:
            raise NotImplementedError
        self.home()

    @retry_session
    def text(self, text, enter=True):
        """bug in wda for now"""
        if enter:
            text += '\n'
        self.session.send_keys(text)

    def clear_app(self, package):
        print('Clearing app data not implemented on iOS')

    def install_app(self, filePath, **kwargs):
        """
        Install the application on the device

        Args:
            filepath: full path to the 'app' or 'ipa' file to be installed on the device

        Returns:
            process

        """
        return self.idb.install_app(filePath)

    def uninstall_app(self, package):
        """
        Uninstall the application from the device

        Args:
            package: package name

        Returns:
            process

        """
        return self.idb.uninstall_app(package)

    def start_app(self, package, *args):
        """
        Start the application and activity

        Args:
            package: package name

        Returns:
            process

        """
        return self.idb.start_app(package)

    def stop_app(self, package):
        """
        Stop the application

        Args:
            package: package name

        Returns:
            process

        """
        return self.idb.stop_app(package)

    def get_ip_address(self):
        """
        get ip address from webDriverAgent

        Returns:
            raise if no IP address has been found, otherwise return the IP address

        """
        return self.driver.status()['ios']['ip']

    def device_status(self):
        """
        show status return by webDriverAgent
        Return dicts of infos
        """
        return self.driver.status()

    def _touch_point_by_orientation(self, tuple_xy):
        """
        Convert image coordinates to physical display coordinates, the arbitrary point (origin) is upper left corner
        of the device physical display

        Args:
            tuple_xy: image coordinates (x, y)

        Returns:

        """
        x, y = tuple_xy

        # use correct w and h due to now orientation
        # _size 只对应竖直时候长宽
        now_orientation = self.orientation

        if now_orientation in [PORTRAIT, PORTRAIT_UPSIDEDOWN]:
            width, height = self._size['width'], self._size["height"]
        else:
            height, width = self._size['width'], self._size["height"]

        # check if not get screensize when touching
        if not width or not height:
            # use snapshot to get current resuluton
            self.snapshot()

        x, y = XYTransformer.up_2_ori(
            (x, y),
            (width, height),
            now_orientation
        )
        return x, y

    def _check_orientation_change(self):
        pass

if __name__ == "__main__":
    start = time.time()
    ios = IOS("http://10.254.51.239:8100")

    ios.snapshot()
    # ios.touch((242 * 2 + 10, 484 * 2 + 20))

    # ios.start_app("com.tencent.xin")
    ios.home()
    ios.start_app('com.apple.mobilesafari')
    ios.touch((88, 88))
    ios.stop_app('com.apple.mobilesafari')
    ios.swipe((100, 100), (800, 100))

    print(ios.device_status())
    print(ios.get_ip_address())
