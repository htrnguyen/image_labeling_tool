import json

import cv2
import numpy as np

# Đọc file JSON
image_name = '1'

with open(f"./output/{image_name}.json", 'r') as f:
    data = json.load(f)

# Mở ảnh
image_path = f"./images/{image_name}.jpg"
image = cv2.imread(image_path)

# Kiểm tra xem ảnh có được mở thành công hay không
if image is None:
    print(f"Error: Could not open or find the image '{image_path}'.")
    exit()

# Lấy kích thước màn hình
screen_width = 1920
screen_height = 1080

# Lấy kích thước ảnh gốc
img_height, img_width = image.shape[:2]

# Tính toán tỷ lệ để scale ảnh vừa với màn hình
scale_x = screen_width / img_width
scale_y = screen_height / img_height
scale = min(scale_x, scale_y)

# Resize ảnh để vừa với màn hình
resized_image = cv2.resize(image, (int(img_width * scale), int(img_height * scale)))

# Danh sách các màu để đánh dấu các từ (words)
colors = [(255, 0, 0), (0, 255, 0), (128, 0, 128), (0, 128, 255), (255, 0, 255)]

# Duyệt qua các label trong JSON và vẽ lên ảnh
for item in data['form']:
    box = item['box']
    label = item['label']
    
    # Vẽ polygon cho toàn bộ label
    pts = np.array(box, np.int32)
    pts = pts.reshape((-1, 1, 2))
    cv2.polylines(resized_image, [pts], isClosed=True, color=(0, 0, 255), thickness=2)

    # Duyệt qua các words trong label và vẽ polygon
    for i, word in enumerate(item['words']):
        word_box = word['box']
        color = colors[i % len(colors)]  # Chọn màu theo thứ tự từ danh sách
        word_pts = np.array(word_box, np.int32)
        word_pts = word_pts.reshape((-1, 1, 2))
        cv2.polylines(resized_image, [word_pts], isClosed=True, color=color, thickness=2)

# Hiển thị ảnh với tùy chọn thu phóng
zoom_factor = 1.0

while True:
    zoomed_image = cv2.resize(resized_image, (0, 0), fx=zoom_factor, fy=zoom_factor)
    cv2.imshow('Labeled Image', zoomed_image)

    key = cv2.waitKey(0) & 0xFF
    if key == ord('+'):
        zoom_factor *= 1.1  # Phóng to 10%
    elif key == ord('-'):
        zoom_factor *= 0.9  # Thu nhỏ 10%
    elif key == 27:  # ESC để thoát
        break

cv2.destroyAllWindows()
