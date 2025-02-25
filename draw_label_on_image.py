import json

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

image_name = "0001"

# Đường dẫn đến file ảnh gốc
image_path = f"./images/{image_name}.jpg"

# Đường dẫn đến file JSON chứa thông tin bounding box
json_path = f"./output/{image_name}.json"

# Đọc ảnh gốc
image = cv2.imread(image_path)
if image is None:
    print(f"Error: Unable to open image file {image_path}")
    exit(1)

# Đọc file JSON
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Hàm để tính góc xoay của hình chữ nhật
def get_rotation_angle(box):
    # Lấy các điểm của hình chữ nhật
    p1, p2, _, _ = box
    # Tính vector từ p1 đến p2
    vector = np.array(p2) - np.array(p1)
    # Tính góc giữa vector và trục x
    angle = np.degrees(np.arctan2(vector[1], vector[0]))
    return angle

# Hàm để vẽ các bounding box lên hình ảnh
def draw_boxes(image, form_data, draw_words=False):
    pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_image)
    font = ImageFont.truetype("arial.ttf", 20)  # Sử dụng font Arial hỗ trợ tiếng Việt

    for item in form_data:
        # Vẽ bounding box cho label
        box = item['box']
        text = item['text']
        label = item['label']
        pts = np.array(box, np.int32).reshape((-1, 1, 2))
        cv2.polylines(image, [pts], True, (0, 255, 0), 1)
        draw.text(tuple(box[0]), f'{label}: {text}', font=font, fill=(0, 0, 255))

        # Vẽ bounding box cho từng từ (word) nếu cần
        if draw_words:
            words = item.get('words', [])
            drawn_boxes = set()  # Để lưu trữ các bounding box đã vẽ
            for word in words:
                word_box = word['box']
                word_text = word['text']
                word_pts = np.array(word_box, np.int32).reshape((-1, 1, 2))
                word_tuple = tuple(map(tuple, word_box))  # Chuyển thành tuple để lưu trong set

                if word_tuple not in drawn_boxes:
                    cv2.polylines(image, [word_pts], True, (255, 0, 0), 1)
                    draw.text(tuple(word_box[0]), word_text, font=font, fill=(255, 0, 0))
                    drawn_boxes.add(word_tuple)

    return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

# Xác định kích thước màn hình
screen_width = 1600  # Thay đổi nếu cần
screen_height = 800  # Thay đổi nếu cần

# Lấy kích thước gốc của ảnh
original_height, original_width = image.shape[:2]

# Tính tỷ lệ scale
scale_width = screen_width / original_width
scale_height = screen_height / original_height
scale = min(scale_width, scale_height)

# Tính kích thước mới của ảnh
new_width = int(original_width * scale)
new_height = int(original_height * scale)

# Scale ảnh
resized_image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)

# Scale các bounding box và từ (word)
scaled_form_data = []
for item in data['form']:
    scaled_box = [[int(x * scale) for x in point] for point in item['box']]
    scaled_words = []
    for word in item.get('words', []):
        scaled_word_box = [[int(x * scale) for x in point] for point in word['box']]
        scaled_words.append({
            'box': scaled_word_box,
            'text': word['text']
        })
    scaled_form_data.append({
        'box': scaled_box,
        'text': item['text'],
        'label': item['label'],
        'words': scaled_words
    })

# Vẽ bounding box lên ảnh đã scale
resized_image = draw_boxes(resized_image, scaled_form_data, draw_words=True)

# Hiển thị ảnh
cv2.imshow('Scaled Image with Bounding Boxes', resized_image)
cv2.waitKey(0)
cv2.destroyAllWindows()

# Lưu ảnh 
output_path = "image.png"
cv2.imwrite(output_path, resized_image)
print(f"Saved image to {output_path}")
