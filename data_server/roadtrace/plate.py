import cv2
import numpy as np
from ultralytics import YOLO
from rapidocr import RapidOCR

class CarPlateManager:
    def __init__(self, model_path: str):
        print(f"初始化 CarPlateManager，使用模型: {model_path}")
        self.yolo = YOLO(model_path)
        print("CarPlateManager 初始化完成")

        self.ocr = RapidOCR()
        self.plate_db = {
            "ABC-123": {
                "x": 100, 
                "y": 200, 
                "area": 'A', 
                "violations": {
                    "改館噪音": [],
                    "偽造車牌": True,
                    "通緝車輛": True
                }
            },
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

    def recognize_plates(self, yolo_results) -> list:
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
            print("No plate detected")
            return None
        return results

    def update_violation(self, plate_number: str, violation: str) -> None:
        record = self.plate_db[plate_number]

        if "分貝" in violation:
            record["violations"]["改館噪音"].append(violation)
        elif "偽造" in violation:
            record["violations"]["偽造"] = True
        elif "通緝" in violation:
            record["violations"]["wanted"] = True

    def save_violation_image(self, plate_number: str, yolo_results) -> None:
        annotated_image = yolo_results[0].plot()
        violations = self.plate_db[plate_number]["violations"]

        if violations:
        for noise_violation in violations["改館噪音"]:
            cv2.putText(
                annotated_image,
                noise_violation,            # 文字內容
                (20, 20 + text_row * 40),   # 文字位置 (x, y)
                cv2.FONT_HERSHEY_SIMPLEX,   # 字型
                1,                          # 字體大小
                (0, 255, 0),                # 顏色 (B, G, R)，綠色
                2,                          # 線條粗細
                cv2.LINE_AA                 # 抗鋸齒
            )
            text_row += 1
        cv2.imwrite("result.jpg", annotated_image)