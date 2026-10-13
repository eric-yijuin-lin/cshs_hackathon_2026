import cv2
import numpy as np
from ultralytics import YOLO
from rapidocr import RapidOCR

class CarPlateManager:
    def __init__(self):
        self.yolo = YOLO("./best_models/sch-pp85c_plate-641xp(20260917).pt")
        self.ocr = RapidOCR()
        self.plate_db = {
            "ABC-123": {
                "x": 100, 
                "y": 200, 
                "area": 'A', 
                "violations": ["改管噪音", "偽造車牌", "通緝贓車"]
            },
        }
            
    def insert_plate(self, plate_data: dict):
        plate_number = plate_data["plate_number"]
        self.plate_db[plate_number] = {
            "x": plate_data["x"],
            "y": plate_data["y"],
            "area": plate_data["area"],
            "violations": plate_data["violations"]
        }

    def get_plate_data(self, plate_number: str) -> dict:
        return self.plate_db.get(plate_number, None)

    def upsert_plate_location(self, plate_number: str, position: tuple, area: str) -> None:
        if plate_number in self.plate_db:
            self.plate_db[plate_number]["x"] = position[0]
            self.plate_db[plate_number]["y"] = position[1]
            self.plate_db[plate_number]["area"] = area
        else:
            self.plate_db[plate_number] = {
                "x": position[0], 
                "y": position[1], 
                "area":area, 
                "violations": []
            }

    def update_area(self, plate_number: str, area: str) -> None:
        self.ensure_plate_exits(plate_number)
        self.plate_db[plate_number]["area"] = area

    def recognize_plates(self, img_bytes) -> list:
        yolo_results = self.detect_plates(img_bytes)
        annotated_image = yolo_results[0].plot()
        cv2.imwrite("result.jpg", annotated_image)
        
        ocr_results = []
        for result in yolo_results:
            # YOLO 原始影像，型別是 numpy.ndarray
            image = result.orig_img

            for box in result.boxes.xyxy:
                # Tensor -> CPU -> int
                x1, y1, x2, y2 = box.cpu().numpy().astype(int)

                # 裁切 YOLO 找到的車牌
                plate_img = image[y1:y2, x1:x2]

                # OCR：YOLO 已經找好位置，所以關掉文字偵測
                ocr_result = self.ocr(
                    plate_img,
                    use_det=False,
                    use_cls=False,
                    use_rec=True,
                )

                if ocr_result.txts and ocr_result.txts[0].strip():
                    plate_text = ocr_result.txts[0]
                    score = ocr_result.scores[0]
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2

                    ocr_results.append({
                        "plate_number": plate_text,
                        "score": score,
                        "position": (center_x, center_y),
                    })
        return ocr_results

    def detect_plates(self, img_bytes):
        image_array = np.frombuffer(img_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError("Invalid image data")
        
        results = self.yolo.predict(image)
        if len(results[0].boxes) <= 0:
            print("Not plate detected")
            return None
        return results
