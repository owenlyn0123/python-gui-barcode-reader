
from dbr import *
import cv2
from multiprocessing import Process, Queue
import time
import numpy as np


def process_barcode_frame(license, frameQueue, resultQueue, template=None, types=0, types2=0):
    # Create Dynamsoft Barcode Reader
    reader = BarcodeReader()
    # Apply for a trial license: https://www.dynamsoft.com/customer/license/trialLicense
    reader.init_license(license)
    if template is not None and template is not '':
        error = reader.init_runtime_settings_with_string(template)
        if error[0] != EnumErrorCode.DBR_OK:
            print(error[1])
    
    if types != 0:
        settings = reader.get_runtime_settings()
        settings.barcode_format_ids = types
        ret = reader.update_runtime_settings(settings)

    if types2 != 0:
        settings = reader.get_runtime_settings()
        settings.barcode_format_ids_2 = types2
        ret = reader.update_runtime_settings(settings)
        
    settings = reader.get_runtime_settings()
    settings.max_algorithm_thread_count = 1
    reader.update_runtime_settings(settings)

    while True:
        results = None

        try:
            frame = frameQueue.get(False, 10)
            if type(frame) is str:
                break
        except:
            time.sleep(0.01)
            continue
        
        start, end = 0, 0
        try:
            frameHeight, frameWidth, channel = frame.shape[:3]
            start = time.time()
            # results = reader.decode_buffer(frame)
            results = reader.decode_buffer_manually(np.array(frame).tobytes(), frameWidth, frameHeight, frame.strides[0], EnumImagePixelFormat.IPF_RGB_888)
            end = time.time()
        except BarcodeReaderError as error:
            print(error)

        try:
            resultQueue.put([results, (end - start) * 1000], False, 10)
        except:
            pass


class BarcodeManager():
    def __init__(self, license):
        self._reader = BarcodeReader()
        self._reader.init_license(license)
        settings = self._reader.get_runtime_settings()
        settings.max_algorithm_thread_count = 1
        self._reader.update_runtime_settings(settings)
        self._template = None
        self._types = 0
        self._types2 = 0
        self._license = license
        self.frameQueue, self.resultQueue, self.barcodeScanning = None, None, None

    def __decode_buffer(self, frame):
        if frame is None:
            return None, None
        
        if self._template is not None and self._template is not '':
            error = self._reader.init_runtime_settings_with_string(self._template)
            if error[0] != EnumErrorCode.DBR_OK:
                print(error[1])
        
        if self._types != 0:
            settings = self._reader.get_runtime_settings()
            settings.barcode_format_ids = self._types
            ret = self._reader.update_runtime_settings(settings)

        if self._types2 != 0:
            settings = self._reader.get_runtime_settings()
            settings.barcode_format_ids_2 = self._types2
            ret = self._reader.update_runtime_settings(settings)

        start = time.time()
        results = self._reader.decode_buffer(frame)
        end = time.time()
        return frame, [results, (end - start) * 1000]

    def decode_frame(self, frame):
        return self.__decode_buffer(frame)

    def decode_file(self, filename):
        frame = cv2.imread(filename)
        return self.__decode_buffer(frame)

    def set_template(self, template):
        self._template = template

    def set_barcode_types(self, types):
        self._types = types
    
    def set_barcode_types_2(self, types):
        self._types2 = types

    def create_barcode_process(self):
        self.destroy_barcode_process()

        size = 1
        self.frameQueue = Queue(size)
        self.resultQueue = Queue(size)
        self.barcodeScanning = Process(target=process_barcode_frame, args=(self._license, self.frameQueue, self.resultQueue, self._template, self._types, self._types2))
        self.barcodeScanning.start()
    
    def destroy_barcode_process(self):
        if self.frameQueue is not None:
            self.frameQueue.put("")
            self.frameQueue = None

        if self.barcodeScanning is not None:
            self.barcodeScanning.join()
            self.barcodeScanning = None

        if self.frameQueue is not None:
            self.frameQueue.close()
            self.frameQueue = None

        if self.resultQueue is not None:
            self.resultQueue.close()
            self.resultQueue = None

    def append_frame(self, frame):
        try:
            self.frameQueue.put(frame.copy(), False, 10)
        except:
            pass

    def peek_results(self):
        try:
            return self.resultQueue.get(False, 10)
        except:
            return None
    