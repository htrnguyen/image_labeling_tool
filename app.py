#!/usr/bin/env python3

import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

from PIL import ExifTags, Image, ImageTk


class LabelingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Labeling Tool")
        self.root.state('zoomed')  # Mở ứng dụng ở chế độ full màn hình
        # Cấu hình đường dẫn
        self.image_folder = "images"  # Folder chứa ảnh
        self.output_folder = "output"  # Folder chứa output JSON
        os.makedirs(self.output_folder, exist_ok=True)  # Tạo folder nếu chưa tồn tại
        self.current_image_path = None
        self.image = None
        self.photo = None
        self.labels = []
        self.id_counter = 1
        self.current_label = None
        self.word_boxes = []
        self.is_labeling_word = False
        self.current_word_index = 0
        self.scale_x = 1.0  # Tỷ lệ scale theo chiều rộng
        self.scale_y = 1.0  # Tỷ lệ scale theo chiều cao
        self.image_list = []  # Danh sách ảnh
        self.current_image_index = 0  # Chỉ mục ảnh hiện tại
        self.current_points = []  # Lưu trữ các điểm hiện tại của bounding box
        self.word_box_points = []  # Lưu trữ các điểm hiện tại của bounding box cho từng từ
        self.thumbnail_refs = {}  # Lưu trữ tham chiếu đến thumbnail để tránh garbage collection
        # Giao diện chính
        self.setup_ui()
        self.load_image_list()

    def setup_ui(self):
        # Chia giao diện thành 3 cột với tỷ lệ phù hợp
        self.frame_left = tk.Frame(self.root, width=300, bg="lightgray")  # Tăng kích thước cột timeline
        self.frame_center = tk.Frame(self.root, bg="white")
        self.frame_right = tk.Frame(self.root, width=350, bg="lightblue")  # Tăng kích thước cột bên phải
        self.frame_left.pack(side=tk.LEFT, fill=tk.Y)
        self.frame_center.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        self.frame_right.pack(side=tk.RIGHT, fill=tk.Y)
        # Cột 1: Timeline ảnh với thumbnail
        self.thumbnail_frame = tk.Frame(self.frame_left, bg="lightgray")
        self.thumbnail_frame.pack(expand=True, fill=tk.BOTH)
        self.scrollbar = tk.Scrollbar(self.thumbnail_frame, orient=tk.VERTICAL)
        self.canvas_timeline = tk.Canvas(self.thumbnail_frame, yscrollcommand=self.scrollbar.set, bg="lightgray")
        self.scrollbar.config(command=self.canvas_timeline.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas_timeline.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        self.timeline_frame = tk.Frame(self.canvas_timeline, bg="lightgray")
        self.canvas_timeline.create_window((0, 0), window=self.timeline_frame, anchor="nw")
        # Cột 2: Canvas để hiển thị ảnh
        self.canvas = tk.Canvas(self.frame_center, bg="white")
        self.canvas.pack(expand=True, fill=tk.BOTH)
        # Bind các sự kiện chuột
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        self.canvas.bind("<Button-3>", self.cancel_current_label)  # Bind chuột phải để hủy đánh label hiện tại
        # Cột 3: Các nút chức năng và bảng nhập thông tin
        self.info_frame = tk.Frame(self.frame_right, bg="lightblue")
        self.info_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(self.info_frame, text="Text:", bg="lightblue").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.text_entry = tk.Entry(self.info_frame)
        self.text_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        tk.Label(self.info_frame, text="Label Name:", bg="lightblue").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.label_entry = tk.Entry(self.info_frame)
        self.label_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        tk.Label(self.info_frame, text="Linking (e.g., '1 2'):", bg="lightblue").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.linking_entry = tk.Entry(self.info_frame)
        self.linking_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        self.save_button = tk.Button(self.info_frame, text="Save Label", command=self.save_current_label)
        self.save_button.grid(row=3, column=0, columnspan=2, pady=10)
        self.save_and_next_button = tk.Button(self.info_frame, text="Save and Next", command=self.save_and_next)
        self.save_and_next_button.grid(row=4, column=0, columnspan=2, pady=5)
        self.clear_labels_button = tk.Button(self.info_frame, text="Clear Labels", command=self.clear_labels)
        self.clear_labels_button.grid(row=5, column=0, columnspan=2, pady=5)
        # Nút chỉnh sửa ID và Linking
        self.edit_id_button = tk.Button(self.info_frame, text="Edit ID", command=self.edit_selected_id)
        self.edit_id_button.grid(row=6, column=0, columnspan=2, pady=5)
        self.edit_linking_button = tk.Button(self.info_frame, text="Edit Linking", command=self.edit_selected_linking)
        self.edit_linking_button.grid(row=7, column=0, columnspan=2, pady=5)
        # Label thông báo
        self.status_label = tk.Label(self.info_frame, text="Please draw a bounding box.", bg="lightblue", fg="blue")
        self.status_label.grid(row=8, column=0, columnspan=2, pady=10)
        # Hiển thị danh sách labels
        self.label_listbox = tk.Listbox(self.frame_right, selectmode=tk.SINGLE)
        self.label_listbox.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)
        self.label_listbox.bind("<Double-Button-1>", self.on_label_select)
        self.delete_button = tk.Button(self.frame_right, text="Delete Selected Label", command=self.delete_selected_label)
        self.delete_button.pack(fill=tk.X, padx=10, pady=5)

    def load_image_list(self):
        """Tải danh sách ảnh từ folder."""
        if os.path.exists(self.image_folder):
            # Xóa nội dung cũ trong canvas_timeline
            self.canvas_timeline.delete("all")
            self.image_list = []
            x_offset, y_offset = 10, 10
            max_height = 0
            num_columns = 3  # Số cột muốn hiển thị
            thumbnail_size = 100  # Kích thước thumbnail
            padding = 10  # Khoảng cách giữa các thumbnail
            for i, filename in enumerate(os.listdir(self.image_folder)):
                if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                    image_path = os.path.join(self.image_folder, filename)
                    self.image_list.append(image_path)
                    # Tạo thumbnail
                    img = Image.open(image_path)
                    img = self.rotate_image_based_on_exif(img)  # Xoay ảnh dựa trên EXIF
                    img.thumbnail((thumbnail_size, thumbnail_size))  # Resize thumbnail
                    photo = ImageTk.PhotoImage(img)
                    self.thumbnail_refs[image_path] = photo  # Lưu tham chiếu
                    # Vẽ thumbnail lên canvas
                    self.canvas_timeline.create_image(x_offset, y_offset, anchor=tk.NW, image=photo, tags=f"thumbnail_{i}")
                    # Kiểm tra xem ảnh đã có label hay chưa
                    base_name = os.path.splitext(os.path.basename(image_path))[0]
                    json_path = os.path.join(self.output_folder, f"{base_name}.json")
                    text_color = "green" if os.path.exists(json_path) else "black"
                    # Vẽ tên ảnh bên dưới thumbnail
                    self.canvas_timeline.create_text(
                        x_offset + thumbnail_size // 2, y_offset + thumbnail_size + 5, text=filename, fill=text_color, font=("Arial", 8),
                        anchor=tk.N, tags=f"label_{i}", width=thumbnail_size  # Đặt width để tự động xuống dòng nếu tên ảnh quá dài
                    )
                    # Bind sự kiện chọn ảnh
                    self.canvas_timeline.tag_bind(f"thumbnail_{i}", "<Button-1>", lambda e, path=image_path: self.select_image(path))
                    self.canvas_timeline.tag_bind(f"label_{i}", "<Button-1>", lambda e, path=image_path: self.select_image(path))
                    # Cập nhật vị trí
                    x_offset += thumbnail_size + padding
                    max_height = max(max_height, thumbnail_size + 25)
                    if (i + 1) % num_columns == 0:
                        x_offset = 10
                        y_offset += max_height
                        max_height = 0
            self.canvas_timeline.config(scrollregion=self.canvas_timeline.bbox("all"))

    def select_image(self, image_path):
        """Chọn một ảnh và làm nổi bật nó."""
        # Reset tất cả các thumbnail và tên ảnh về trạng thái mặc định
        for i in range(len(self.image_list)):
            base_name = os.path.splitext(os.path.basename(self.image_list[i]))[0]
            json_path = os.path.join(self.output_folder, f"{base_name}.json")
            text_color = "green" if os.path.exists(json_path) else "black"
            self.canvas_timeline.itemconfig(f"label_{i}", fill=text_color)
        # Tìm và làm nổi bật thumbnail và tên ảnh được chọn
        index = self.image_list.index(image_path)
        self.canvas_timeline.itemconfig(f"label_{index}", fill="red")  # Đổi màu chữ thành đỏ
        self.canvas_timeline.itemconfig(f"thumbnail_{index}", state=tk.NORMAL)  # Nổi bật thumbnail
        # Tải ảnh được chọn
        self.load_image(image_path)

    def load_image(self, image_path):
        """Tải và hiển thị ảnh."""
        self.current_image_path = image_path
        self.current_image_index = self.image_list.index(image_path)
        self.image = Image.open(image_path)
        self.image = self.rotate_image_based_on_exif(self.image)  # Xoay ảnh dựa trên EXIF
        self.canvas.delete("all")
        # Resize ảnh để vừa với canvas nhưng giữ đúng tỷ lệ
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        img_width, img_height = self.image.size
        aspect_ratio = img_width / img_height
        if canvas_width / canvas_height > aspect_ratio:
            new_height = canvas_height
            new_width = int(new_height * aspect_ratio)
        else:
            new_width = canvas_width
            new_height = int(new_width / aspect_ratio)
        self.scale_x = img_width / new_width  # Tỷ lệ gốc / hiển thị
        self.scale_y = img_height / new_height  # Tỷ lệ gốc / hiển thị
        resized_image = self.image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(resized_image)
        # Tính toán vị trí để căn giữa ảnh trên canvas
        x_offset = (canvas_width - new_width) // 2
        y_offset = (canvas_height - new_height) // 2
        self.canvas.create_image(x_offset + new_width // 2, y_offset + new_height // 2, image=self.photo, anchor=tk.CENTER, tags="image")
        # Vẽ lưới tọa độ phù hợp với kích thước ảnh
        self.draw_grid(x_offset, y_offset, new_width, new_height)
        # Bind sự kiện di chuyển chuột để hiển thị tọa độ động
        self.canvas.bind("<Motion>", lambda event: self.show_mouse_coordinates(event, x_offset, y_offset))
        # Reset các ô nhập liệu khi tải ảnh mới
        self.reset_input_fields()
        # Tải labels từ file JSON nếu có
        self.load_labels()
        # Cập nhật danh sách labels trong Listbox
        self.update_label_listbox()
        self.status_label.config(text="Please draw a bounding box.")  # Reset thông báo

    def rotate_image_based_on_exif(self, image):
        """Xoay ảnh dựa trên thông tin EXIF."""
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            exif = dict(image._getexif().items())
            if exif[orientation] == 3:
                image = image.rotate(180, expand=True)
            elif exif[orientation] == 6:
                image = image.rotate(270, expand=True)
            elif exif[orientation] == 8:
                image = image.rotate(90, expand=True)
        except (AttributeError, KeyError, IndexError):
            # Trường hợp ảnh không có thông tin EXIF hoặc không có thông tin Orientation
            pass
        return image

    def draw_grid(self, x_offset, y_offset, width, height):
        """Vẽ lưới tọa độ phù hợp với kích thước ảnh."""
        grid_size = 10  # Kích thước mỗi ô lưới
        for x in range(0, width, grid_size):
            self.canvas.create_line(x_offset + x, y_offset, x_offset + x, y_offset + height, fill="gray", dash=(2, 2))
        for y in range(0, height, grid_size):
            self.canvas.create_line(x_offset, y_offset + y, x_offset + width, y_offset + y, fill="gray", dash=(2, 2))

    def show_mouse_coordinates(self, event, x_offset, y_offset):
        """Hiển thị tọa độ hiện tại của con trỏ chuột."""
        # Kiểm tra xem con trỏ chuột có nằm trong vùng ảnh hay không
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        img_width, img_height = self.image.size
        aspect_ratio = img_width / img_height
        if canvas_width / canvas_height > aspect_ratio:
            new_height = canvas_height
            new_width = int(new_height * aspect_ratio)
        else:
            new_width = canvas_width
            new_height = int(new_width / aspect_ratio)
        x_offset = (canvas_width - new_width) // 2
        y_offset = (canvas_height - new_height) // 2
        if x_offset <= event.x < x_offset + new_width and y_offset <= event.y < y_offset + new_height:
            # Chuyển đổi tọa độ từ hệ tọa độ hiển thị sang hệ tọa độ gốc
            original_x = int((event.x - x_offset) * self.scale_x)
            original_y = int((event.y - y_offset) * self.scale_y)
            self.status_label.config(text=f"Mouse Position: ({original_x}, {original_y})")
        else:
            self.status_label.config(text="Mouse is outside the image area.")

    def reset_input_fields(self):
        """Reset tất cả các ô nhập liệu."""
        self.text_entry.delete(0, tk.END)
        self.label_entry.delete(0, tk.END)
        self.linking_entry.delete(0, tk.END)
        self.text_entry.config(state="normal")  # Đảm bảo Text Entry không bị vô hiệu hóa
        self.label_entry.config(state="normal")  # Đảm bảo Label Name Entry không bị vô hiệu hóa
        self.current_label = None
        self.is_labeling_word = False
        self.word_boxes = []
        self.current_word_index = 0
        self.current_points = []
        self.word_box_points = []
        self.canvas.delete("point", "line", "word_point", "word_line")  # Xóa các điểm và đường vẽ tạm thời

    def load_labels(self):
        """Tải labels từ file JSON nếu có."""
        base_name = os.path.splitext(os.path.basename(self.current_image_path))[0]
        json_path = os.path.join(self.output_folder, f"{base_name}.json")
        if os.path.exists(json_path):
            with open(json_path, "r") as f:
                data = json.load(f)
            self.labels = data.get("form", [])
            for label in self.labels:
                if "points" in label:
                    label["box"] = label.pop("points")  # Thay thế points thành box
                for word in label.get("words", []):
                    if isinstance(word.get("box"), tuple):
                        word["box"] = list(word["box"])  # Chuyển tuple thành danh sách
                    if not isinstance(word.get("box"), list) or len(word["box"]) != 4:
                        print(f"Invalid word box: {word['box']}. Setting to default [(0, 0), (0, 0), (0, 0), (0, 0)].")
                        word["box"] = [(0, 0), (0, 0), (0, 0), (0, 0)]  # Thiết lập giá trị mặc định
            self.redraw_labels()
        else:
            self.labels = []

    def save_labels(self):
        """Lưu labels vào file JSON."""
        if not self.current_image_path:
            return
        base_name = os.path.splitext(os.path.basename(self.current_image_path))[0]
        json_path = os.path.join(self.output_folder, f"{base_name}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"form": self.labels}, f, indent=4, ensure_ascii=False)
        print(f"Labels saved to {json_path}")
        # Cập nhật giao diện thời gian thực
        self.update_thumbnail_status()

    def update_thumbnail_status(self):
        """Cập nhật trạng thái của thumbnail sau khi lưu label."""
        base_name = os.path.splitext(os.path.basename(self.current_image_path))[0]
        json_path = os.path.join(self.output_folder, f"{base_name}.json")
        text_color = "green" if os.path.exists(json_path) else "black"
        index = self.image_list.index(self.current_image_path)
        self.canvas_timeline.itemconfig(f"label_{index}", fill=text_color)

    def clear_labels(self):
        """Xóa tất cả labels."""
        self.labels = []
        self.canvas.delete("label")
        self.update_label_listbox()
        self.status_label.config(text="All labels cleared.")
        self.save_labels()  # Lưu lại danh sách rỗng vào file JSON

    def update_label_listbox(self):
        """Cập nhật danh sách labels trong Listbox."""
        self.label_listbox.delete(0, tk.END)
        for label in self.labels:
            linking_info = ", ".join([str(id) for pair in label.get("linking", []) for id in pair]) or "No linking"
            self.label_listbox.insert(tk.END, f"ID: {label['id']} | Text: {label['text']} | Linking: {linking_info}")

    def on_label_select(self, event):
        """Xử lý khi chọn một label từ Listbox."""
        selection = self.label_listbox.curselection()
        if selection:
            index = selection[0]
            label = self.labels[index]
            self.text_entry.delete(0, tk.END)
            self.text_entry.insert(0, label["text"])
            self.text_entry.config(state="disabled")  # Không cho phép chỉnh sửa Text
            self.label_entry.delete(0, tk.END)
            self.label_entry.insert(0, label["label"])
            self.label_entry.config(state="disabled")  # Không cho phép chỉnh sửa Label Name
            self.linking_entry.delete(0, tk.END)
            self.linking_entry.insert(0, " ".join([str(id) for pair in label.get("linking", []) for id in pair]))

    def edit_selected_id(self):
        """Chỉnh sửa ID của label đã chọn."""
        selection = self.label_listbox.curselection()
        if selection:
            index = selection[0]
            label = self.labels[index]
            new_id = simpledialog.askinteger("Edit ID", "Enter new ID:", initialvalue=label["id"])
            if new_id is not None:
                label["id"] = new_id
                self.update_label_listbox()
                self.save_labels()  # Lưu thay đổi vào file JSON
                self.status_label.config(text=f"ID updated to {new_id}.")

    def edit_selected_linking(self):
        """Chỉnh sửa Linking của label đã chọn."""
        selection = self.label_listbox.curselection()
        if selection:
            index = selection[0]
            label = self.labels[index]
            linking_input = simpledialog.askstring("Edit Linking", "Enter new linking (e.g., '1 2'):")
            if linking_input is not None:
                try:
                    ids = [int(id) for id in linking_input.split()]
                    if len(ids) == 1:
                        linking_data = [[ids[0]]]
                    else:
                        linking_data = [ids]
                    label["linking"] = linking_data
                    self.update_label_listbox()
                    self.save_labels()  # Lưu thay đổi vào file JSON
                    self.status_label.config(text="Linking updated.")
                except ValueError:
                    messagebox.showerror("Error", "Invalid input. Please enter valid IDs separated by spaces.")

    def delete_selected_label(self):
        """Xóa label được chọn."""
        selection = self.label_listbox.curselection()
        if selection:
            index = selection[0]
            label_to_delete = self.labels[index]
            self.labels.pop(index)
            self.redraw_labels()
            self.update_label_listbox()
            self.status_label.config(text="Label deleted.")
            # Kiểm tra xem label cần xóa có là current_label hay không
            if self.current_label and self.current_label["id"] == label_to_delete["id"]:
                self.cancel_current_label(None)
            # Lưu lại danh sách labels vào file JSON
            self.save_labels()

    def save_current_label(self):
        """Lưu label hiện tại."""
        text = self.text_entry.get().strip()
        label_name = self.label_entry.get().strip()
        linking_input = self.linking_entry.get().strip()
        # Kiểm tra xem Text và Label Name có rỗng hay không
        if not text:
            self.status_label.config(text="Error: Text cannot be empty.")
            return
        if not label_name:
            self.status_label.config(text="Error: Label Name cannot be empty.")
            return
        # Nếu đang trong quá trình đánh label
        if self.current_label:
            self.current_label["text"] = text
            self.current_label["label"] = label_name
            # Xử lý linking
            if linking_input:
                try:
                    ids = [int(id) for id in linking_input.split()]
                    if len(ids) == 1:
                        linking_data = [[ids[0]]]
                    else:
                        linking_data = [ids]
                    self.current_label["linking"] = linking_data
                except ValueError:
                    self.status_label.config(text="Error: Invalid linking input. Please enter valid IDs separated by spaces.")
                    return
            else:
                self.current_label["linking"] = []
            # Xử lý words
            words = text.split()
            self.current_label["words"] = [{"text": word} for word in words]  # Khởi tạo danh sách words
            if len(words) == 1:
                # Trường hợp chỉ có 1 từ
                self.current_label["words"][0]["box"] = self.current_label["box"]
                # Kiểm tra xem label đã tồn tại hay chưa
                existing_label = next((label for label in self.labels if label["id"] == self.current_label["id"]), None)
                if existing_label:
                    # Ghi đè label hiện tại
                    existing_label.update(self.current_label)
                else:
                    self.labels.append(self.current_label)
                self.redraw_labels()
                self.update_label_listbox()
                self.status_label.config(text="Label saved for single word.")
            else:
                # Trường hợp có nhiều từ
                self.word_boxes = self.current_label["words"]
                self.current_word_index = 0
                self.is_labeling_word = True
                self.status_label.config(text=f"Please draw 4 points for the word: '{words[self.current_word_index]}'")
            # Lưu labels vào file JSON ngay lập tức
            self.save_labels()
            return
        # Reset các ô nhập liệu sau khi lưu label
        self.reset_input_fields()
        # Lưu labels vào file JSON
        self.save_labels()
        # Cập nhật giao diện thời gian thực
        self.update_thumbnail_status()
        self.status_label.config(text="Label saved successfully.")

    def save_and_next(self):
        """Lưu nhãn hiện tại và chuyển sang ảnh tiếp theo."""
        self.save_current_label()  # Lưu nhãn hiện tại
        if self.current_image_index < len(self.image_list) - 1:
            next_image_path = self.image_list[self.current_image_index + 1]
            self.load_image(next_image_path)
        else:
            self.status_label.config(text="This is the last image.")

    def on_mouse_press(self, event):
        if not self.is_labeling_word:
            if len(self.current_points) < 4:
                self.current_points.append((event.x, event.y))
                self.canvas.create_oval(event.x-2, event.y-2, event.x+2, event.y+2, fill="red", tags="point")
                if len(self.current_points) > 1:
                    self.canvas.create_line(self.current_points[-2][0], self.current_points[-2][1], event.x, event.y, fill="red", tags="line")
                if len(self.current_points) == 4:
                    # Vẽ đường nối giữa điểm cuối và điểm đầu
                    self.canvas.create_line(self.current_points[-1][0], self.current_points[-1][1], self.current_points[0][0], self.current_points[0][1], fill="red", tags="line")
                    self.finalize_label()
        else:
            if len(self.word_box_points) < 4:
                self.word_box_points.append((event.x, event.y))
                self.canvas.create_oval(event.x-2, event.y-2, event.x+2, event.y+2, fill="green", tags="word_point")
                if len(self.word_box_points) > 1:
                    self.canvas.create_line(self.word_box_points[-2][0], self.word_box_points[-2][1], event.x, event.y, fill="green", tags="word_line")
                if len(self.word_box_points) == 4:
                    # Vẽ đường nối giữa điểm cuối và điểm đầu
                    self.canvas.create_line(self.word_box_points[-1][0], self.word_box_points[-1][1], self.word_box_points[0][0], self.word_box_points[0][1], fill="green", tags="word_line")
                    self.save_word_label(self.word_box_points)
                    self.word_box_points = []

    def on_mouse_drag(self, event):
        pass  # Không cần xử lý kéo thả khi đánh label cho từng từ

    def on_mouse_release(self, event):
        pass  # Không cần xử lý nhả chuột khi đánh label cho từng từ

    def finalize_label(self):
        if len(self.current_points) == 4:
            # Chuyển đổi tọa độ về kích thước gốc của ảnh
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            img_width, img_height = self.image.size
            aspect_ratio = img_width / img_height
            if canvas_width / canvas_height > aspect_ratio:
                new_height = canvas_height
                new_width = int(new_height * aspect_ratio)
            else:
                new_width = canvas_width
                new_height = int(new_width / aspect_ratio)
            x_offset = (canvas_width - new_width) // 2
            y_offset = (canvas_height - new_height) // 2
            original_points = []
            for point in self.current_points:
                original_point = (
                    int((point[0] - x_offset) * self.scale_x),
                    int((point[1] - y_offset) * self.scale_y)
                )
                original_points.append(original_point)
            self.current_label = {
                "box": original_points,  # Thay thế points thành box
                "text": "",
                "label": "",
                "words": [],
                "id": self.id_counter,
                "linking": []  # Mặc định linking rỗng
            }
            self.id_counter += 1
            self.text_entry.delete(0, tk.END)
            self.label_entry.delete(0, tk.END)
            self.status_label.config(text="Please enter Text and Label Name.")
            self.current_points = []
            self.redraw_labels()
        else:
            print("Not enough points to finalize label.")

    def redraw_labels(self):
        """Vẽ lại tất cả labels trên canvas."""
        self.canvas.delete("label")
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        img_width, img_height = self.image.size
        aspect_ratio = img_width / img_height
        if canvas_width / canvas_height > aspect_ratio:
            new_height = canvas_height
            new_width = int(new_height * aspect_ratio)
        else:
            new_width = canvas_width
            new_height = int(new_width / aspect_ratio)
        x_offset = (canvas_width - new_width) // 2
        y_offset = (canvas_height - new_height) // 2
        for label in self.labels:
            # Chuyển đổi tọa độ từ kích thước gốc sang kích thước hiển thị
            scaled_box = []
            for point in label["box"]:
                scaled_point = (
                    int(point[0] / self.scale_x) + x_offset,
                    int(point[1] / self.scale_y) + y_offset
                )
                scaled_box.append(scaled_point)
            # Vẽ đa giác cho box tổng
            self.canvas.create_polygon(*[coord for point in scaled_box for coord in point], outline="blue", fill="", tags="label")
            for word in label["words"]:
                if "box" in word:
                    # Đảm bảo word["box"] là một danh sách chứa 4 điểm
                    if isinstance(word["box"], tuple):
                        word["box"] = list(word["box"])  # Chuyển tuple thành danh sách
                    if not isinstance(word.get("box"), list) or len(word["box"]) != 4:
                        print(f"Invalid word box: {word['box']}. Skipping this word.")
                        continue  # Bỏ qua word này nếu box không hợp lệ
                    # Chuyển đổi tọa độ về kích thước hiển thị
                    scaled_word_box = [
                        (int(point[0] / self.scale_x) + x_offset, int(point[1] / self.scale_y) + y_offset)
                        for point in word["box"]
                    ]
                    print(f"Drawing word box: {scaled_word_box}")
                    self.canvas.create_polygon(*[coord for point in scaled_word_box for coord in point], outline="green", fill="", tags="label")

    def correct_coordinates(self, points):
        """Chỉnh sửa tọa độ nếu chúng nằm ngoài giới hạn hoặc không hợp lệ."""
        corrected_points = []
        for point in points:
            x, y = point
            x = max(0, min(x, self.image.width))
            y = max(0, min(y, self.image.height))
            corrected_points.append((x, y))
        return corrected_points

    def save_word_label(self, points):
        """Lưu bbox cho từng từ."""
        if self.current_word_index < len(self.word_boxes):
            word = self.word_boxes[self.current_word_index]
            # Đảm bảo points là danh sách chứa 4 điểm
            if len(points) == 4:
                corrected_points = self.correct_coordinates(points)
                word["box"] = corrected_points  # Lưu dưới dạng danh sách 4 điểm
                print(f"Saved word box: {word['box']}")
                self.current_word_index += 1
                if self.current_word_index < len(self.word_boxes):
                    # Vẫn còn từ cần đánh bbox
                    next_word = self.word_boxes[self.current_word_index]["text"]
                    self.status_label.config(text=f"Please draw 4 points for the word: '{next_word}'")
                else:
                    # Hoàn thành đánh bbox cho tất cả các từ
                    self.is_labeling_word = False
                    self.labels.append(self.current_label)
                    self.redraw_labels()
                    self.update_label_listbox()
                    self.reset_input_fields()
                    self.status_label.config(text="Labeling complete. Please enter linking information.")
                # Lưu labels vào file JSON ngay lập tức
                self.save_labels()
            else:
                print(f"Invalid points for word box: {points}")
                self.status_label.config(text="Error: Invalid points for word box.")
        else:
            print("Current word index out of range.")

    def save_linking(self):
        """Lưu thông tin linking."""
        linking_input = self.linking_entry.get().strip()
        if not linking_input:
            # Nếu không nhập gì, mặc định linking rỗng
            linking_data = []
        else:
            try:
                # Tách các ID bằng dấu cách và chuyển đổi thành list số nguyên
                ids = [int(id) for id in linking_input.split()]
                # Chuyển danh sách ID thành định dạng list trong list
                if len(ids) == 1:
                    linking_data = [[ids[0]]]
                else:
                    linking_data = [ids]
            except ValueError:
                self.status_label.config(text="Error: Invalid input. Please enter valid IDs separated by spaces.")
                return
            # Lưu linking vào label cuối cùng
            if self.labels:
                self.labels[-1]["linking"] = linking_data
                self.save_labels()  # Lưu thay đổi vào file JSON
                self.status_label.config(text="Linking saved.")
                self.linking_entry.delete(0, tk.END)
            else:
                self.status_label.config(text="No label available to save linking.")

    def cancel_current_label(self, event):
        """Hủy bỏ label hiện tại khi click chuột phải."""
        if self.current_label:
            print("Canceling current label.")
            self.current_label = None
            self.redraw_labels()
            self.reset_input_fields()
            self.status_label.config(text="Current label canceled. Please draw a new bounding box.")
        else:
            print("No current label to cancel.")
            self.status_label.config(text="No current label to cancel.")

if __name__ == "__main__":
    root = tk.Tk()
    app = LabelingApp(root)
    root.mainloop()