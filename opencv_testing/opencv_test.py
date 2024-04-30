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

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))


def generate_rect(width, height, x_offset, y_offset, end_x_offset=1, end_y_offset=1, color=(255, 255, 255)):
    # If rectangle is centered both horiz. and vert.
    if (end_y_offset == 1 and end_x_offset == 1):
        top_left = (int(width * x_offset), int(height * y_offset))
        bottom_right = (int(width - top_left[0]), int(height - top_left[1]))
    # If rectangle is offcenter both horiz. and vert.
    elif (end_x_offset != 1 and end_y_offset != 1):
        top_left = (int(width * x_offset), int(height * y_offset))
        bottom_right = (int(width * end_x_offset), int(height * end_y_offset))
    # If rectangle is centered only horizontally
    elif (end_y_offset != 1):
        top_left = (int(width * x_offset), int(height * y_offset))
        bottom_right = (int(width - top_left[0]), int(height * end_y_offset))

    rounded_rectangle(frame, top_left, bottom_right, color, radius=0.1, thickness=-1, opacity=0.11)
    
# 16 9 aspect ratio
#page 1
big_x = 0.14
big_y = 0.4045

small_x = 0.42
small_y = 0.33
small_end_y = 0.4

#page 2
league_x = 0.03
league_y = 0.03
league_end_x = 0.375
league_end_y = 0.065




print(duration)
i = 1
while True:
    ret, frame = cap.read()
    if not ret:
        break
    i += 1
    # Fade-in effect goalstamp & match-info
    if i < int(duration * 0.1):
        generate_rect(width, height, big_x, big_y)
        generate_rect(width, height, small_x, small_y, end_y_offset=small_end_y)
    
    if i > int(duration* 0.08):
        generate_rect(width, height, league_x, league_y, league_end_x, league_end_y)

    out.write(frame)
    
cap.release()
out.release()
        