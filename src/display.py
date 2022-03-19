from typing import Callable, Dict
from dataclasses import dataclass
import datetime as dt
import enum
import logging
from pathlib import Path
import random
import sys

from waveshare_epd import epd4in2
from PIL import Image, ImageDraw, ImageFont
import PIL


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


@dataclass(repr=False, order=False)
class Event:
    target_face: bool
    dt: dt.datetime


@enum.unique
class LogicResultTypes(enum.Enum):
    is_tired_target = enum.auto()
    is_target = enum.auto()
    little_lost = enum.auto()
    unknown = enum.auto()
    no_target = enum.auto()
    nothing = enum.auto()


class Logic:

    state_expiration_time: int  # sec
    tired_time: int  # min

    def __init__(self, state_expiration_time: int, tired_time: int):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.debug('Init logic...')
        self.state_expiration_time = state_expiration_time
        self.tired_time = tired_time
        self.state = False
        self.earliest_dt: dt.datetime = dt.datetime(1970, 1, 1)
        self.latest_dt: dt.datetime = dt.datetime(1970, 1, 1)
        self.little_lost = False

    def create_state(self, event: Event) -> None:
        self._logger.debug('New state')
        self.state = True
        self.earliest_dt = event.dt
        self.latest_dt = event.dt

    def update_state(self, event: Event) -> None:
        self._logger.debug('Update state')
        self.state = True
        self.latest_dt = event.dt
        self.little_lost = False

    def destroy_state(self) -> None:
        self._logger.debug('Destroy state')
        self.state = False

    def is_tired(self) -> bool:
        return self.latest_dt - self.earliest_dt >= dt.timedelta(minutes=self.tired_time)

    def is_expired(self, event: Event) -> bool:
        return event.dt - self.latest_dt >= dt.timedelta(seconds=self.state_expiration_time)

    def is_little_lost(self, event: Event) -> bool:
        if event.dt - self.latest_dt >= dt.timedelta(seconds=int(self.state_expiration_time/6)):
            self.little_lost = True
            return True
        return False

    def process(self, event: Event) -> LogicResultTypes:
        if event.target_face:
            if self.state:
                self.update_state(event)
                if self.is_tired():
                    return LogicResultTypes.is_tired_target
            else:
                self.create_state(event)
            return LogicResultTypes.is_target
        else:
            if self.state:
                if self.is_expired(event):
                    self._logger.debug('Is expired state')
                    self.destroy_state()
                elif self.is_little_lost(event):
                    return LogicResultTypes.little_lost
                else:
                    return LogicResultTypes.nothing
            return LogicResultTypes.no_target


class Display:
    picture_dir = Path('pic')

    def __init__(self, vflip: bool = False, hflip: bool = False):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.debug('Init display...')
        self.vflip = vflip
        self.hflip = hflip
        self.logic_picture_map: Dict[LogicResultTypes, Callable] = {
            LogicResultTypes.is_tired_target: self.tired_target,
            LogicResultTypes.is_target: self.target_detected,
            LogicResultTypes.little_lost: self.little_lost_target,
            LogicResultTypes.unknown: self.unknown_target,
            LogicResultTypes.no_target: self.no_target,
            LogicResultTypes.nothing: self.nothing_interesting,
        }
        self.target_pics = list([x for x in (self.picture_dir / Path('target')).iterdir()])
        self._logger.debug(self.target_pics)
        self.tired_target_pics = list([x for x in (self.picture_dir / Path('tired_target')).iterdir()])
        self.no_target_pics = list([x for x in (self.picture_dir / Path('no_target')).iterdir()])
        self.current_screen: LogicResultTypes = LogicResultTypes.no_target
        self.display = epd4in2.EPD()
        self.display.init()

    def display_image(self, file):
        img = Image.open(file)
        if self.hflip:
            raise NotImplemented()
        if self.vflip:
            img = img.rotate(180)
        self.display.display(self.display.getbuffer(img))

    def target_detected(self):
        self.display_image(random.choice(self.target_pics))

    def tired_target(self):
        self.display_image(random.choice(self.tired_target_pics))

    def little_lost_target(self):
        self.display_image(random.choice(self.no_target_pics))

    def unknown_target(self):
        pass

    def no_target(self):
        self.display_image(random.choice(self.no_target_pics))

    def nothing_interesting(self):
        pass

    def set_screen(self, event: LogicResultTypes) -> None:
        if event not in (self.current_screen, LogicResultTypes.nothing):
            self.logic_picture_map[event]()
            self.current_screen = event
            self._logger.debug('Screen changed')

    def __del__(self):
        self.no_target()
