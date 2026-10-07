from rapidocr import RapidOCR

class CarPlateManager:
    def __init__(self):
        self.ocr = RapidOCR()
        self.plates = {
            "ABC-123": {
                "x": 100, 
                "y": 200, 
                "area": 'A', 
                "is_legal": False
            },
        }

    def upsert_plate(self, plate_data):
        plate_number = plate_data["plate_number"]
        self.plates[plate_number] = {
            "x": plate_data["x"],
            "y": plate_data["y"],
            "area": plate_data["area"],
            "is_legal": plate_data["is_legal"]
        }

    def get_plate_data(self, plate_number):
        return self.plates.get(plate_number, None)

    def recognize_plate(self, yolo_results) -> list:
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
