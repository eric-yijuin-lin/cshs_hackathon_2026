from roadtrace.plate import CarPlateManager
from roadtrace.roadpath import RoadPathManager

class PathTracer:
    def __init__(self):
        self.plate_manager = CarPlateManager()
        self.path_manager = RoadPathManager()

    def trace_plate(self, device_id: str, img_bytes: list):
        area = self.path_manager.get_device_area(device_id)
        if not area:
            raise ValueError(f"找不到對應的區域，device_id = {device_id}")

        ocr_results = self.plate_manager.recognize_plates(img_bytes)
        for result in ocr_results:
            plate_number = result["plate_number"]
            position = result["position"]
            area = self.path_manager.get_device_area(device_id)
            score = result["score"] 
            print(f"偵測到車牌: {plate_number}, 分數: {score}, 位置: {position}, 區域: {area}")

            self.plate_manager.upsert_plate_location(plate_number, position, area)
