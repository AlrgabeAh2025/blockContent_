import torch
import cv2
from models.common import DetectMultiBackend
from utils.general import non_max_suppression, scale_boxes
from utils.torch_utils import select_device
from utils.plots import Annotator, colors
import pathlib

pathlib.PosixPath = pathlib.WindowsPath

def detect_image(weights, image_path, conf_thres=0.25, iou_thres=0.45, device=''):
    device = select_device(device)
    model = DetectMultiBackend(weights, device=device)
    names = model.names

    img0 = cv2.imread(image_path) 
    assert img0 is not None, f"Failed to load image {image_path}"

    # تغيير حجم الصورة لتكون متوافقة مع YOLOv5
    img = cv2.resize(img0, (640, 640), interpolation=cv2.INTER_LINEAR)
    img = img[:, :, ::-1].transpose(2, 0, 1)  # BGR إلى RGB وتغيير الأبعاد
    img = img.copy()  # حل مشكلة stride السلبي
    img = torch.from_numpy(img).to(device)
    img = img.float() / 255.0  # تطبيع القيم بين 0 و1
    if img.ndimension() == 3:
        img = img.unsqueeze(0)

    # الكشف عن الكائنات
    pred = model(img, augment=False, visualize=False)
    pred = non_max_suppression(pred, conf_thres, iou_thres, max_det=1000)
    isThere = False
    confNumber = 0
    label = ""
    # عرض النتائج
    for det in pred:  # لكل صورة
        annotator = Annotator(img0, line_width=3, example=str(names))
        if det is not None and len(det):
            # تحويل المربعات إلى حجم الصورة الأصلية
            det[:, :4] = scale_boxes(img.shape[2:], det[:, :4], img0.shape).round()

            # رسم المربعات التوضيحية
            for *xyxy, conf, cls in det:
                isThere = True
                confNumber = f'{conf:.2f}%'
                label = f"{names[int(cls)]} {conf:.2f}"
                annotator.box_label(xyxy, label, color=colors(int(cls), True))
        
        img_result = annotator.result()

        return [isThere , confNumber , label]
