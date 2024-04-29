import cv2
import os
from PIL import Image, ImageDraw, ImageFont

current_directory = os.path.dirname(os.path.abspath(__file__))
file_name = '16_9.mp4'
file_path = os.path.join(current_directory, file_name)
print("Path to the file:", file_path)

input_video_path = 'opencv_testing/video_16_9.mp4'
output_video_path = 'opencv_testing/16_9_meta.mp4'

cap = cv2.VideoCapture('opencv_testing/video_16_9.mp4')

if not cap.isOpened():
    print('Error opening video')
    exit()

width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = int(cap.get(cv2.CAP_PROP_FPS))

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_video_path, fourcc, 20.0, (width, height))

# 16 9 aspect ratio
aspect_ratio = [16, 9]
logo_box_dim_ratio = 0.35
logo_dim_ratio = 0.2
msg_font_size = 25
icon_dim_ratio = 0.15
overlay_postion_y_offset = 0.92
overlay_postion_x_offset = 0.05

duration = 8 * fps
min_x = round(width * overlay_postion_x_offset)
y_pos = int(height * overlay_postion_y_offset)

i = 1
while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
    image = Image.fromarray(frame)
    i += 1

    temp_image = image.copy()
    draw_temp = ImageDraw.Draw(temp_image)
    
    # Fade-in effect goalstamp & match-info
    if i < int(duration * 0.1):
        cv2.rectangle(frame, (50,50), (200,200), (255,0,0), 3)

    out.write(frame)

cap.release()
out.release()
        