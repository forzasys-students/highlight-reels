import cv2
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def rounded_rectangle(src, top_left, bottom_right, color, radius=1, thickness=1, opacity=1, line_type=cv2.LINE_AA):
    overlay = src.copy()
    #  corners:
    #  p1 - p2
    #  |     |
    #  p4 - p3

    p1 = top_left
    p2 = (bottom_right[0], top_left[1])
    p3 = (bottom_right[0], bottom_right[1])
    p4 = (top_left[0], bottom_right[1])

    height = abs(bottom_right[1] - top_left[1])

    if radius > 1:
        radius = 1

    corner_radius = int(radius * (height/2))

    if thickness < 0:

        #big rect
        top_left_main_rect = (int(p1[0] + corner_radius), int(p1[1]))
        bottom_right_main_rect = (int(p3[0] - corner_radius), int(p3[1]))

        top_left_rect_left = (p1[0], p1[1] + corner_radius)
        bottom_right_rect_left = (p4[0] + corner_radius, p4[1] - corner_radius)

        top_left_rect_right = (p2[0] - corner_radius, p2[1] + corner_radius)
        bottom_right_rect_right = (p3[0], p3[1] - corner_radius)

        all_rects = [
        [top_left_main_rect, bottom_right_main_rect], 
        [top_left_rect_left, bottom_right_rect_left], 
        [top_left_rect_right, bottom_right_rect_right]]

        [cv2.rectangle(src, rect[0], rect[1], color, thickness) for rect in all_rects]

    # draw straight lines
    cv2.line(src, (p1[0] + corner_radius, p1[1]), (p2[0] - corner_radius, p2[1]), color, abs(thickness), line_type)
    cv2.line(src, (p2[0], p2[1] + corner_radius), (p3[0], p3[1] - corner_radius), color, abs(thickness), line_type)
    cv2.line(src, (p3[0] - corner_radius, p4[1]), (p4[0] + corner_radius, p3[1]), color, abs(thickness), line_type)
    cv2.line(src, (p4[0], p4[1] - corner_radius), (p1[0], p1[1] + corner_radius), color, abs(thickness), line_type)

    # draw arcs
    cv2.ellipse(src, (p1[0] + corner_radius, p1[1] + corner_radius), (corner_radius, corner_radius), 180.0, 0, 90, color ,thickness, line_type)
    cv2.ellipse(src, (p2[0] - corner_radius, p2[1] + corner_radius), (corner_radius, corner_radius), 270.0, 0, 90, color , thickness, line_type)
    cv2.ellipse(src, (p3[0] - corner_radius, p3[1] - corner_radius), (corner_radius, corner_radius), 0.0, 0, 90,   color , thickness, line_type)
    cv2.ellipse(src, (p4[0] + corner_radius, p4[1] - corner_radius), (corner_radius, corner_radius), 90.0, 0, 90,  color , thickness, line_type)

    cv2.addWeighted(overlay, opacity, src, 1 - opacity, 0, src)
    return src

def generate_rect(width, height, x_offset, y_offset, end_x=1, end_y=1, color=(255, 255, 255), opacity=0.11):
    # If rectangle is centered both horiz. and vert.
    if (end_x == 1 and end_y == 1):
        top_left = (int(width * x_offset), int(height * y_offset))
        bottom_right = (int(width - top_left[0]), int(height - top_left[1]))
    # If rectangle is offcenter both horiz. and vert.
    elif (end_x != 1 and end_y != 1):
        top_left = (int(width * x_offset), int(height * y_offset))
        bottom_right = (int(width * end_x), int(height * end_y))
    # If rectangle is centered only horizontally
    elif (end_y != 1):
        top_left = (int(width * x_offset), int(height * y_offset))
        bottom_right = (int(width - top_left[0]), int(height * end_y))

    rounded_rectangle(frame, top_left, bottom_right, color, radius=0.1, thickness=-1, opacity=opacity)
    
def generate_center_text(frame, text, font_size, width, height, x_offset, y_offset, end_x=1, end_y=1, color=(0,0,0), thickness=1):
    if (end_x == 1 and end_y == 1):
        center_w = int(width / 2)
        center_h = int(height / 2)
    elif (end_x != 1 and end_y != 1):
        center_w = int(width*x_offset + ((width*end_x - width*x_offset)/2))
        center_h = int(height*y_offset + ((height*end_y - height*y_offset)/2))
    elif (end_y != 1):
        center_w = int(width / 2)
        center_h = int(height*y_offset + ((height*end_y - height*y_offset)/2))
    
    font = cv2.FONT_HERSHEY_DUPLEX
    text_size, _ = cv2.getTextSize(text, font, font_size, thickness)
    text_origin = (int(center_w - text_size[0] / 2), int(center_h + text_size[1] / 2))

    cv2.putText(frame, text, (text_origin[0], text_origin[1]), font, font_size, color, thickness, cv2.LINE_AA)


input_video_path = 'opencv_testing/video_16_9.mp4'
output_video_path = 'opencv_testing/16_9_meta.mp4'

if os.path.exists(output_video_path):
    os.remove(output_video_path)
    print(f"File '{output_video_path}' has been successfully removed.")
else:
    print(f"The file '{output_video_path}' does not exist.")

cap = cv2.VideoCapture(input_video_path)

if not cap.isOpened():
    print('Error opening video')
    exit()

width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = int(cap.get(cv2.CAP_PROP_FPS))
duration = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
font = cv2.FONT_HERSHEY_SIMPLEX
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))



# 16 9 aspect ratio
#page 1
p1_big_x = 0.14
p1_big_y = 0.4045

p1_small_x = 0.31
p1_small_y = 0.33
p1_small_end_y = 0.4
p1_small_font = 2

#page 2
p2_x = 0.03
p2_end_x = 0.375

p2_small_y = 0.03
p2_small_end_y = 0.065
p2_small_font = 1

p2_big_y = 0.081
p2_big_end_y = 0.185

player_y = 0.88
player_end_y = 0.95

#page 3
p3_small_x = 0.35
p3_small_y = 0.51
p3_small_end_y = 0.56
p3_small_font = 1.2

p3_x = 0.34

p3_big_y = 0.58
p3_big_end_y = 0.65

p3_player_end_y = 0.75

i = 1
while True:
    ret, frame = cap.read()
    if not ret:
        break
    i += 1
    # Fade-in effect goalstamp & match-info
    if i < int(duration * 0.1):
        generate_rect(width, height, p1_big_x, p1_big_y)
        generate_rect(width, height, p1_small_x, p1_small_y, end_y=p1_small_end_y)
        generate_center_text(frame, "ALLSVENSKAN", p1_small_font, width, height, p1_small_x, p1_small_y, end_y=p1_small_end_y)
        
    if i > int(duration* 0.08):
        generate_rect(width, height, p2_x, p2_small_y, p2_end_x, p2_small_end_y)
        generate_center_text(frame, "ALLSVENSKAN", p2_small_font, width, height, p2_x, p2_small_y, end_x=p2_end_x, end_y=p2_small_end_y)
        generate_rect(width, height, p2_x, p2_big_y, p2_end_x, p2_big_end_y)

    if i > int(duration * 0.4) and i < (duration * 0.7):
        generate_rect(width, height, p2_x, player_y, p2_end_x, player_end_y)

    if i > (duration * 0.8):
        generate_rect(width, height, p3_small_x, p3_small_y, end_y=p3_small_end_y)
        generate_center_text(frame, "ALLSVENSKAN", p3_small_font, width, height, p3_small_x, p3_small_y, end_y=p3_small_end_y)

        generate_rect(width, height, p3_x, p3_big_end_y, end_y=p3_player_end_y)
        generate_rect(width, height, p3_x, p3_big_y, end_y=p3_big_end_y, opacity=0)
    
    out.write(frame)
    
cap.release()
out.release()
        