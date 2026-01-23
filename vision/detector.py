from ultralytics import YOLO

class LoginDetector:
    def __init__(self, model_path):
        self.model = YOLO(model_path)

    def detect(self, image_path):
        results = self.model(image_path, verbose=False, conf=0.05, iou=0.7)
        detections = []

        # print("results:", results)
        for r in results:
            if r.boxes is None:
                continue
            print("boxes:", r.boxes, len(r.boxes))

            for i in range(len(r.boxes)):
                x1, y1, x2, y2 = map(int, r.boxes.xyxy[i])
                conf = float(r.boxes.conf[i])
                cls = int(r.boxes.cls[i])
                label = r.names[cls]

                detections.append({
                    "label": label,
                    "box": (x1, y1, x2, y2),
                    "conf": conf
                })

        return detections

