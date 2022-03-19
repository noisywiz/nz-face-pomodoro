import datetime as dt
from io import BytesIO
import logging
import sys

import face_recognition
import cv2
import picamera
from PIL import Image
import numpy as np

from src.display import Logic, Event, Display


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


class FaceWorker:
    logic: Logic
    display: Display

    def __init__(self, image_file: str, vflip: bool = False, hflip: bool = False):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.debug('Init encodings...')
        self.video_capture = picamera.PiCamera(resolution=(1024, 768), framerate=2)
        self.known_face_encodings = face_recognition.face_encodings(face_recognition.load_image_file(image_file))[0]
        self.vflip = vflip
        self.hflip = hflip

    def is_target_face(self, frame: np.array) -> bool:
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        # small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(small_frame)
        face_encodings = face_recognition.face_encodings(small_frame, face_locations)
        if face_encodings:
            results = face_recognition.compare_faces([self.known_face_encodings], face_encodings[0])
            if results[0]:
                return True
        return False

    def get_frame(self) -> np.array:
        stream = BytesIO()
        self.video_capture.capture(stream, format='jpeg')
        stream.seek(0)
        r = np.array(Image.open(stream))
        if self.vflip:
            r = np.flipud(r)
        if self.hflip:
            r = np.fliplr(r)
        return r

    def process(self) -> None:
        frame = self.get_frame()
        now = dt.datetime.utcnow()
        is_target_face = self.is_target_face(frame)
        event = Event(dt=now, target_face=is_target_face)
        result = self.logic.process(event)
        self._logger.debug(result)
        self.display.set_screen(result)  # display magic here

    def shut_down_screen(self):
        pass

    def run(self, **kwargs):
        self.display = Display(vflip=kwargs['display_vflip'], hflip=kwargs['display_hflip'])
        self.logic = Logic(state_expiration_time=kwargs['state_expiration_time'], tired_time=kwargs['tired_time'])
        while True:
            try:
                self.process()
            except Exception as e:
                self._logger.error(e)
                self.shut_down_screen()
                exit()
