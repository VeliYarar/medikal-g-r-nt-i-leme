import cv2
import numpy as np
import os
import time
from ultralytics import YOLO

LEKE_HSV = {
    "sari":     ([20,  60,  80], [35, 255, 255]),
    "kirmizi":  ([0, 80, 80], [10, 255, 255]),
    "kirmizi2": ([160, 80, 80], [180, 255, 255]),
    "yesil":    ([36, 50, 50], [85, 255, 255]),
    "mavi":     ([86, 60, 60], [130, 255, 255]),
    "kahverengi": ([10, 70, 20], [20, 255, 200]),
    "siyah":    ([0, 0, 0], [180, 255, 50])
}
barkod_rect_oran = (0.09, 0.60, 0.78, 0.72)

def oran_to_pixel_rect(oransal_rect, box):
    x1, y1, x2, y2, *_ = box
    w = x2 - x1
    h = y2 - y1
    bx1 = int(x1 + oransal_rect[0]*w)
    by1 = int(y1 + oransal_rect[1]*h)
    bx2 = int(x1 + oransal_rect[2]*w)
    by2 = int(y1 + oransal_rect[3]*h)
    return (bx1, by1, bx2, by2)

def tespit_ve_ciz_leke(img, mask_dict, barkod_rect=None, min_area=10, max_area=800):
    toplam_leke_sayisi = 0
    kontur_listesi = []  # Her bir dikdörtgenin bilgisi

    for mask_name, mask in mask_dict.items():
        if mask.shape[:2] != img.shape[:2]:
            mask = cv2.resize(mask, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
        mask3 = cv2.merge([mask, mask, mask])
        masked_img = cv2.bitwise_and(img, mask3)
        hsv = cv2.cvtColor(masked_img, cv2.COLOR_BGR2HSV)
        for renk, (low, high) in LEKE_HSV.items():
            lower = np.array(low, dtype=np.uint8)
            upper = np.array(high, dtype=np.uint8)
            mask_leke = cv2.inRange(hsv, lower, upper)
            mask_leke = cv2.bitwise_and(mask_leke, mask)
            mask_leke = cv2.morphologyEx(mask_leke, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
            if barkod_rect is not None:
                bx1, by1, bx2, by2 = barkod_rect
                mask_leke[by1:by2, bx1:bx2] = 0
            contours, _ = cv2.findContours(mask_leke, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if min_area < area < max_area:
                    toplam_leke_sayisi += 1
                    kontur_listesi.append((mask_name, renk, cnt))
    return toplam_leke_sayisi, kontur_listesi

def analiz_merkez_ve_mesafe_gorsel(img, class_boxes):
    if not ('ped' in class_boxes and 'ped_center' in class_boxes):
        return img, False
    px1, py1, px2, py2, _ = class_boxes['ped']
    cx1, cy1, cx2, cy2, _ = class_boxes['ped_center']
    ped_w, ped_h = px2 - px1, py2 - py1
    mesafe_sol = abs(cx1 - px1)
    mesafe_sag = abs(px2 - cx2)
    mesafe_ust = abs(cy1 - py1)
    mesafe_alt = abs(py2 - cy2)
    cv2.rectangle(img, (px1, py1), (px2, py2), (255,0,0), 2)
    cv2.rectangle(img, (cx1, cy1), (cx2, cy2), (0,255,0), 2)
    cv2.line(img, (px1, cy1), (cx1, cy1), (0,0,255), 2)
    cv2.line(img, (cx2, cy1), (px2, cy1), (0,0,255), 2)
    cv2.line(img, (cx1, py1), (cx1, cy1), (0,0,255), 2)
    cv2.line(img, (cx1, cy2), (cx1, py2), (0,0,255), 2)
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, f'Sol: {mesafe_sol}px', (px1+5, cy1-10), font, 0.6, (0,0,255), 2)
    cv2.putText(img, f'Sag: {mesafe_sag}px', (cx2+5, cy1-10), font, 0.6, (0,0,255), 2)
    cv2.putText(img, f'Ust: {mesafe_ust}px', (cx1+5, py1+20), font, 0.6, (0,0,255), 2)
    cv2.putText(img, f'Alt: {mesafe_alt}px', (cx1+5, cy2+20), font, 0.6, (0,0,255), 2)
    tolerans = 0.1
    simetrik = (abs(mesafe_sol - mesafe_sag)/ped_w < tolerans) and (abs(mesafe_ust - mesafe_alt)/ped_h < tolerans)
    simetri_text = "Simetrik" if simetrik else "Kayik"
    cv2.putText(img, simetri_text, (px1+10, py1-10), font, 0.9, (255,0,255), 3)
    return img, simetrik

# ---- ANA KLASÖR İŞLEYİCİ ----
UPLOADS_DIR = os.path.expanduser("~/Desktop/uploads")
PROCESSED_DIR = os.path.expanduser("~/Desktop/processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

model_path = "best.pt"
model = YOLO(model_path)

# Daha önce işlenenleri kaydet
already_processed = set(os.listdir(PROCESSED_DIR))

print(f"Klasör izleniyor: {UPLOADS_DIR}")
while True:
    files = [f for f in os.listdir(UPLOADS_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    for fname in files:
        input_path = os.path.join(UPLOADS_DIR, fname)
        output_path = os.path.join(PROCESSED_DIR, fname)
        if fname in already_processed:
            continue
        try:
            print(f"İşleniyor: {fname}")
            img_path = input_path
            results = model.predict(img_path, conf=0.1, verbose=False)
            names = results[0].names

            mask_dict = {}
            paket_box = None
            class_boxes = {}
            for box, cls in zip(results[0].boxes.xyxy, results[0].boxes.cls):
                class_name = names[int(cls)]
                box_int = tuple(box.cpu().numpy().astype(int))
                if class_name == "paket":
                    paket_box = box_int
                if class_name in ["ped", "ped_center"]:
                    class_boxes[class_name] = (*box_int, 1.0)
            if hasattr(results[0], 'masks') and results[0].masks is not None:
                for m, cls in zip(results[0].masks.data, results[0].boxes.cls):
                    class_name = names[int(cls)]
                    if class_name in ["ped", "ped_center"]:
                        mask = m.cpu().numpy().astype(np.uint8) * 255
                        mask_dict[class_name] = mask

            print("Maskeler:", list(mask_dict.keys()))
            barkod_rect = None
            if paket_box is not None:
                barkod_rect = oran_to_pixel_rect(barkod_rect_oran, paket_box)
                print("Barkod (pixel):", barkod_rect)

            if mask_dict:
                img = cv2.imread(img_path)
                img_out = img.copy()
                toplam_leke_sayisi, kontur_listesi = tespit_ve_ciz_leke(
                    img, mask_dict, barkod_rect=barkod_rect
                )
                print("Toplam tespit edilen leke:", toplam_leke_sayisi)
                img_show = img_out.copy()

                if toplam_leke_sayisi > 6:
                    cv2.putText(img_show, "LEKE YOK!", (30,50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0,255,0), 4)
                else:
                    for mask_name, renk, cnt in kontur_listesi:
                        x, y, w, h = cv2.boundingRect(cnt)
                        cv2.rectangle(img_show, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        cv2.putText(img_show, f"{mask_name}:{renk}", (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
                    if toplam_leke_sayisi > 0:
                        cv2.putText(img_show, "LEKE VAR!", (30,50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0,0,255), 4)
                    else:
                        cv2.putText(img_show, "LEKE YOK!", (30,50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0,255,0), 4)

                if barkod_rect is not None:
                    bx1, by1, bx2, by2 = barkod_rect
                    cv2.rectangle(img_show, (bx1, by1), (bx2, by2), (255,0,255), 2)
                    cv2.putText(img_show, "BARKOD", (bx1, by1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,0,255), 2)

                img_show, simetrik = analiz_merkez_ve_mesafe_gorsel(img_show, class_boxes)

                # Görseli daha küçük pencerede gösterme
                # max_win_w = 1180
                # max_win_h = 900
                # h, w = img_show.shape[:2]
                # fx, fy = min(max_win_w/w, 1.0), min(max_win_h/h, 1.0)
                # img_show = cv2.resize(img_show, (int(w*fx), int(h*fy)), interpolation=cv2.INTER_AREA)
                # cv2.imshow("Leke + Simetri + Barkod", img_show)
                # cv2.waitKey(0)
                # cv2.destroyAllWindows()
            else:
                img_show = cv2.imread(img_path)
                cv2.putText(img_show, "Ped ve/veya Ped Center segmentasyonu bulunamadı!", (30,50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 3)

            # KAYDET
            cv2.imwrite(output_path, img_show)
            print(f"Kaydedildi: {output_path}")
            already_processed.add(fname)
        except Exception as e:
            print(f"Hata ({fname}):", e)
    time.sleep(2)  # Her 2 saniyede bir kontrol et
