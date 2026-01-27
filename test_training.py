"""
YOLO Model Testing Script
=========================
Script đơn giản để test model YOLO đã training
Chỉ cần file .pt và ảnh test
"""

import cv2
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from typing import Tuple, List, Dict


class YOLODetector:
    """Class để test model YOLO đã training"""

    def __init__(self, model_path: str):
        """
        Args:
            model_path: Đường dẫn đến file .pt đã training
        """
        self.model_path = model_path
        self.model = None
        self.load_model()

    def load_model(self):
        """Load model .pt đã training"""
        try:
            from ultralytics import YOLO

            self.model = YOLO(self.model_path)
            print(f"✅ Loaded model: {self.model_path}")

        except ImportError:
            # Fallback sang YOLOv5 nếu không có ultralytics
            print("⚠️ Ultralytics not found, trying YOLOv5...")
            import torch

            self.model = torch.hub.load(
                "ultralytics/yolov5", "custom", path=self.model_path
            )
            print(f"✅ Loaded YOLOv5 model: {self.model_path}")

        except Exception as e:
            print(f"❌ Error: {e}")
            raise

    def test_image(self, image_path: str, conf=0.25) -> Tuple[List[Dict], np.ndarray]:
        """
        Test model trên 1 ảnh

        Args:
            image_path: Đường dẫn ảnh test
            conf: Ngưỡng confidence (0-1)

        Returns:
            detections: List tọa độ và label
            annotated_image: Ảnh có bounding box
        """
        # Đọc ảnh
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"❌ Không đọc được ảnh: {image_path}")

        # Chạy detection
        results = self.model(image, conf=conf)
        result = results[0]

        # Lấy tọa độ từng object
        detections = []
        for i, box in enumerate(result.boxes):
            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
            conf_score = float(box.conf[0])
            cls_id = int(box.cls[0])
            label = self.model.names[cls_id]

            detections.append(
                {
                    "id": i,
                    "label": label,
                    "confidence": conf_score,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "center_x": (x1 + x2) / 2,
                    "center_y": (y1 + y2) / 2,
                    "width": x2 - x1,
                    "height": y2 - y1,
                }
            )

        # Lấy ảnh có box vẽ sẵn
        annotated_image = result.plot()

        return detections, annotated_image

    def print_results(self, detections: List[Dict]):
        """In kết quả ra console"""
        print("\n" + "=" * 70)
        print(f"🎯 Phát hiện {len(detections)} đối tượng:")
        print("=" * 70)

        for det in detections:
            print(f"\n#{det['id']} - {det['label']} ({det['confidence']:.2%})")
            print(
                f"  📍 Tọa độ: ({det['x1']}, {det['y1']}) → ({det['x2']}, {det['y2']})"
            )
            print(f"  📐 Center: ({det['center_x']:.0f}, {det['center_y']:.0f})")
            print(f"  📏 Kích thước: {det['width']}x{det['height']}px")

    def save_image(self, image: np.ndarray, output_path: str):
        """Lưu ảnh kết quả"""
        cv2.imwrite(output_path, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        print(f"\n💾 Đã lưu ảnh: {output_path}")

    def show_image(self, image: np.ndarray, title="Detection Result"):
        """Hiển thị ảnh"""
        plt.figure(figsize=(12, 8))
        plt.imshow(image)
        plt.axis("off")
        plt.title(title, fontsize=14, fontweight="bold")
        plt.tight_layout()
        plt.show()


# ==================== CÁCH SỬ DỤNG ====================


def test_single_image(model_path: str, image_path: str):
    """
    Test model trên 1 ảnh

    Args:
        model_path: Đường dẫn file .pt
        image_path: Đường dẫn ảnh test
    """
    # 1. Load model
    detector = YOLODetector(model_path)

    # 2. Test ảnh
    detections, annotated_img = detector.test_image(image_path, conf=0.25)

    # 3. In kết quả
    detector.print_results(detections)

    # 4. Hiển thị ảnh
    detector.show_image(annotated_img)

    # 5. Lưu ảnh kết quả
    output_path = "result_" + Path(image_path).name
    detector.save_image(annotated_img, output_path)

    return detections, annotated_img


# ==================== MAIN ====================

if __name__ == "__main__":

    # 🔧 CẤU HÌNH - THAY ĐỔI Ở ĐÂY
    MODEL_PATH = "E:\\asfy\\facebook\\tool_playwright\\vision\\models\\login.pt"
    IMAGE_PATH = "E:\\asfy\\facebook\\tool_playwright\\screen.png"

    # 🚀 CHẠY TEST
    print("🚀 Bắt đầu test model...")
    detections, result_img = test_single_image(MODEL_PATH, IMAGE_PATH)

    # 📊 Ví dụ truy xuất tọa độ
    print("\n" + "=" * 70)
    print("📊 TỔNG HỢP TỌA ĐỘ:")
    print("=" * 70)
    for det in detections:
        print(
            f"{det['label']:15s} | BBox: ({det['x1']:4d},{det['y1']:4d}) - ({det['x2']:4d},{det['y2']:4d}) | Conf: {det['confidence']:.2%}"
        )

    print("\n✅ Hoàn thành!")
