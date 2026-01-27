"""
YOLO Detection Class
====================
Class đơn giản để đọc kết quả từ model YOLO đã training
Input: đường dẫn ảnh + file .pt
Output: object chứa label và tọa độ
"""

import cv2
import numpy as np
from typing import List, Dict, Optional


class YOLOReader:
    """Class đọc và trả về tọa độ từ YOLO model"""

    def __init__(self, model_path: str):
        """
        Khởi tạo model

        Args:
            model_path: Đường dẫn file .pt đã training
        """
        self.model_path = model_path
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load model YOLO"""
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
            print(f"Da load model: {self.model_path}")
        except ImportError:
            print("Cai dat ultralytics: pip install ultralytics")
            raise
        except Exception as e:
            print(f"Loi load model: {e}")
            raise

    def detect(self, image_path: str, conf: float = 0.25) -> List[Dict]:
        """
        Phát hiện object trong ảnh

        Args:
            image_path: Đường dẫn ảnh cần detect
            conf: Ngưỡng confidence (0-1), mặc định 0.25

        Returns:
            List[Dict]: Danh sách object detect được, mỗi object có:
                - label: Tên class
                - confidence: Độ tin cậy (0-1)
                - x1, y1: Tọa độ góc trên-trái
                - x2, y2: Tọa độ góc dưới-phải
                - center_x, center_y: Tọa độ tâm
                - width, height: Kích thước bbox

        Example:
            >>> detector = YOLOReader("model.pt")
            >>> results = detector.detect("image.png")
            >>> for obj in results:
            >>>     print(f"{obj['label']} tại ({obj['x1']}, {obj['y1']})")
        """
        # Đọc ảnh
        image = cv2.imread(image_path)
        if image is None:
            raise FileNotFoundError(f"Không tìm thấy ảnh: {image_path}")

        # Chạy detection
        results = self.model(image, conf=conf, verbose=False)
        
        # Parse kết quả
        detections = []
        for box in results[0].boxes:
            # Lấy tọa độ
            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
            
            # Tạo object kết quả
            obj = {
                "label": self.model.names[int(box.cls[0])],
                "confidence": float(box.conf[0]),
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "center_x": int((x1 + x2) / 2),
                "center_y": int((y1 + y2) / 2),
                "width": x2 - x1,
                "height": y2 - y1,
            }
            detections.append(obj)

        return detections

    def detect_from_bytes(self, img_bytes: bytes, conf: float = 0.25) -> List[Dict]:
        """
        Detect trực tiếp từ bytes (Playwright screenshot)
        """

        # bytes → numpy → image
        img_np = np.frombuffer(img_bytes, np.uint8)
        image = cv2.imdecode(img_np, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError("Decode image failed")

        results = self.model(image, conf=conf, verbose=False)

        detections = {}

        for box in results[0].boxes:
            label = self.model.names[int(box.cls[0])]
            conf = float(box.conf[0])

            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())

            obj = {
                "confidence": conf,
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "center_x": int((x1 + x2) / 2),
                "center_y": int((y1 + y2) / 2),
                "width": x2 - x1,
                "height": y2 - y1,
            }

            # Nếu label chưa tồn tại → gán luôn
            if label not in detections:
                detections[label] = obj
            else:
                # Nếu đã tồn tại → lấy box có confidence cao hơn
                if conf > detections[label]["confidence"]:
                    detections[label] = obj


        return detections


    def get_by_label(self, image_path: str, label: str, conf: float = 0.25) -> Optional[Dict]:
        """
        Lấy object đầu tiên có label cụ thể

        Args:
            image_path: Đường dẫn ảnh
            label: Tên label cần tìm
            conf: Ngưỡng confidence

        Returns:
            Dict hoặc None nếu không tìm thấy
        """
        detections = self.detect(image_path, conf)
        for obj in detections:
            if obj["label"] == label:
                return obj
        return None

    def get_all_by_label(self, image_path: str, label: str, conf: float = 0.25) -> List[Dict]:
        """
        Lấy tất cả object có label cụ thể

        Args:
            image_path: Đường dẫn ảnh
            label: Tên label cần tìm
            conf: Ngưỡng confidence

        Returns:
            List các object tìm được
        """
        detections = self.detect(image_path, conf)
        return [obj for obj in detections if obj["label"] == label]
