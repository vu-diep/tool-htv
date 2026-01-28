"""
YOLO Detection Class with OCR
==============================
Class đọc kết quả từ model YOLO và OCR text trong bbox
Input: đường dẫn ảnh + file .pt
Output: object chứa label, tọa độ và text content
"""

import cv2
import numpy as np
from typing import List, Dict, Optional
import pytesseract
from PIL import Image


class YOLOReader:
    """Class đọc và trả về tọa độ từ YOLO model + OCR text"""

    def __init__(self, model_path: str, dpr: float = 1.0):
        """
        Khởi tạo model

        Args:
            model_path: Đường dẫn file .pt đã training
            dpr: Device Pixel Ratio
        """
        self.model_path = model_path
        self.dpr = dpr
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

    def _extract_text(self, image: np.ndarray, bbox: Dict, lang: str = 'vie+eng') -> str:
        """
        Trích xuất text từ bounding box
        
        Args:
            image: Ảnh gốc (numpy array)
            bbox: Dictionary chứa x1, y1, x2, y2
            lang: Ngôn ngữ OCR ('vie' cho tiếng Việt, 'eng' cho tiếng Anh)
        
        Returns:
            Text đọc được từ bbox
        """
        try:
            # Crop vùng bbox
            x1, y1, x2, y2 = bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2']
            
            # Thêm padding để OCR tốt hơn
            padding = 5
            y1_pad = max(0, y1 - padding)
            y2_pad = min(image.shape[0], y2 + padding)
            x1_pad = max(0, x1 - padding)
            x2_pad = min(image.shape[1], x2 + padding)
            
            cropped = image[y1_pad:y2_pad, x1_pad:x2_pad]
            
            # Tiền xử lý ảnh để OCR tốt hơn
            # Convert sang grayscale
            gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
            
            # Tăng contrast
            gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
            
            # Threshold
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # OCR với Tesseract
            text = pytesseract.image_to_string(
                thresh, 
                lang=lang,
                config='--psm 7'  # PSM 7: Single text line
            ).strip()
            
            return text
            
        except Exception as e:
            print(f"⚠️ Lỗi OCR: {e}")
            return ""

    def detect(self, img_bytes: bytes, conf: float = 0.25, 
               extract_text: bool = False, ocr_lang: str = 'vie+eng') -> Dict:
        """
        Detect với tự động scale theo DPR và OCR text
        
        Args:
            img_bytes: Screenshot bytes
            conf: Confidence threshold
            extract_text: Có trích xuất text hay không
            ocr_lang: Ngôn ngữ OCR ('vie', 'eng', 'vie+eng')
        
        Returns:
            Dictionary với format: {label: {confidence, x1, y1, x2, y2, center_x, center_y, width, height, text}}
        """
        img_np = np.frombuffer(img_bytes, np.uint8)
        image = cv2.imdecode(img_np, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError("Decode image failed")


        results = self.model(image, conf=conf, verbose=False)
        detections = {}

        for box in results[0].boxes:
            label = self.model.names[int(box.cls[0])]
            conf_score = float(box.conf[0])
            
            # Lấy tọa độ gốc
            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
            
            # Scale về viewport nếu DPR != 1
            if self.dpr != 1.0:
                x1, y1 = int(x1 / self.dpr), int(y1 / self.dpr)
                x2, y2 = int(x2 / self.dpr), int(y2 / self.dpr)

            obj = {
                "confidence": conf_score,
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "center_x": int((x1 + x2) / 2),
                "center_y": int((y1 + y2) / 2),
                "width": x2 - x1,
                "height": y2 - y1,
            }
            
            # Trích xuất text nếu được yêu cầu
            if extract_text:
                # Dùng tọa độ gốc (trước khi scale) để crop từ ảnh gốc
                bbox_original = {
                    'x1': int(box.xyxy[0][0].cpu().numpy()),
                    'y1': int(box.xyxy[0][1].cpu().numpy()),
                    'x2': int(box.xyxy[0][2].cpu().numpy()),
                    'y2': int(box.xyxy[0][3].cpu().numpy())
                }
                text = self._extract_text(image, bbox_original, ocr_lang)
                obj['text'] = text
            else:
                obj['text'] = None

            if label not in detections:
                detections[label] = obj
            else:
                if conf_score > detections[label]["confidence"]:
                    detections[label] = obj

        return detections

    def read_text_from_label(self, img_bytes: bytes, label: str, 
                            conf: float = 0.25, dpr: float = 1.0,
                            ocr_lang: str = 'vie+eng') -> Optional[str]:
        """
        Đọc text từ label cụ thể
        
        Args:
            img_bytes: Screenshot bytes
            label: Tên label cần đọc text
            conf: Confidence threshold
            dpr: Device Pixel Ratio
            ocr_lang: Ngôn ngữ OCR
            
        Returns:
            Text content hoặc None nếu không tìm thấy
            
        Example:
            >>> detector = YOLOReader("model.pt")
            >>> screenshot = await page.screenshot()
            >>> username = detector.read_text_from_label(screenshot, "tai_khoan")
            >>> print(f"Username hiện tại: {username}")
        """
        detections = self.detect(img_bytes, conf=conf, extract_text=True, ocr_lang=ocr_lang)
        
        if label in detections:
            return detections[label]['text']
        return None

    def get_all_text(self, img_bytes: bytes, conf: float = 0.25,  ocr_lang: str = 'vie+eng') -> Dict[str, str]:
        """
        Đọc text từ tất cả labels
        
        Returns:
            Dictionary {label: text_content}
            
        Example:
            >>> texts = detector.get_all_text(screenshot)
            >>> print(texts)
            {'tai_khoan': 'user@gmail.com', 'mat_khau': '********'}
        """
        detections = self.detect(img_bytes, conf=conf, extract_text=True, ocr_lang=ocr_lang)
        
        return {label: obj['text'] for label, obj in detections.items()}

    def save_cropped_region(self, img_bytes: bytes, label: str, 
                           output_path: str, conf: float = 0.25) -> bool:
        """
        Lưu vùng đã crop của label cụ thể (để debug OCR)
        
        Args:
            img_bytes: Screenshot bytes
            label: Label cần crop
            output_path: Đường dẫn lưu ảnh
            
        Returns:
            True nếu thành công
        """
        img_np = np.frombuffer(img_bytes, np.uint8)
        image = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
        
        detections = self.detect(img_bytes, conf=conf)
        
        if label not in detections:
            print(f"❌ Không tìm thấy label: {label}")
            return False
        
        obj = detections[label]
        
        # Crop với tọa độ đã scale về
        # Nhưng phải scale ngược về để crop từ ảnh gốc
        if self.dpr != 1.0:
            x1 = int(obj['x1'] * self.dpr)
            y1 = int(obj['y1'] * self.dpr)
            x2 = int(obj['x2'] * self.dpr)
            y2 = int(obj['y2'] * self.dpr)
        else:
            x1, y1, x2, y2 = obj['x1'], obj['y1'], obj['x2'], obj['y2']
        
        cropped = image[y1:y2, x1:x2]
        cv2.imwrite(output_path, cropped)
        print(f"💾 Đã lưu: {output_path}")
        return True