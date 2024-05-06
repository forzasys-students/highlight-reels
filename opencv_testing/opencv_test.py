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

def generate_rect(x_offset, y_offset, end_x=1, end_y=1, color=(255, 255, 255), opacity=0.11, width=1920, height=1080, text=[], font_scale=1):
    global font_style
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

    if text:
        text_size = cv2.getTextSize(max(text, key=len), font_style, ((bottom_right[1]-top_left[1])*font_scale)/22, 2)
        text_width = int(text_size[0][0])
        new_top_left = ["",""] 
        new_bottom_right = ["",""]
        new_top_left[1] = top_left[1]
        new_bottom_right[1] = bottom_right[1]
        
        if (end_x == 1 and end_y == 1):
            if len(text) == 2:
                new_top_left[0] = int(top_left[0] - text_width)
                new_bottom_right[0] = int(bottom_right[0] + text_width)
            else:
                new_top_left[0] = int(top_left[0] - text_width/2)
                new_bottom_right[0] = int(bottom_right[0] + text_width/2)
        elif (end_y != 1):
            if len(text) == 2:
                new_top_left[0] = int(top_left[0] - text_width)
                new_bottom_right[0] = int(bottom_right[0] + text_width)
            else:
                new_top_left[0] = int(top_left[0] - text_width/2)
                new_bottom_right[0] = int(bottom_right[0] + text_width/2)
        elif (end_x != 1 and end_y != 1):
                new_top_left = top_left[0]
                new_bottom_right[0] = int(bottom_right[0] + text_width/2)

        top_left = tuple(new_top_left)
        bottom_right = tuple(new_bottom_right)

    rounded_rectangle(frame, top_left, bottom_right, color, radius=0.1, thickness=-1, opacity=opacity)
    return bottom_right[1]-top_left[1] # Return height of rect for calculating font size

def generate_center_text(frame, text, x_offset, y_offset, end_x=1, end_y=1, position=0, color=(0,0,0), thickness=2, width=1920, height=1080, rect_h=0, font_scale=1):
    global font_style
    if (end_x == 1 and end_y == 1):
        center_w = int(width / 2)
        center_h = int(height / 2)
        if position != 0:
            w_offset = int((width - 2*(x_offset*width))*position)
            center_w = center_w - w_offset
    elif (end_x != 1 and end_y != 1):
        center_w = int(width*x_offset + ((width*end_x - width*x_offset)/2))
        center_h = int(height*y_offset + ((height*end_y - height*y_offset)/2))
        if position != 0:
            w_offset = int((width*end_x - width*x_offset)*position)
            center_w = center_w - w_offset
    elif (end_y != 1):
        center_w = int(width / 2)
        center_h = int(height*y_offset + ((height*end_y - height*y_offset)/2))
        if position != 0:
            w_offset = int((width - 2*(x_offset*width))*position)
            center_w = center_w - w_offset
    
    if rect_h != 0:
        font_scale = (rect_h)/22 # Scale the font, 22 meaning the standard size of the font in pixels
    else:
        font_scale = font_scale
    
    text_size, _ = cv2.getTextSize(text, font_style, font_scale, thickness)
    
    text_origin = (int(center_w - text_size[0] / 2), int(center_h + text_size[1] / 2))

    cv2.putText(frame, text, (text_origin[0], text_origin[1]), font_style, font_scale, color, thickness, cv2.LINE_AA)

def is_image(var):
    return isinstance(var, Image.Image)

def generate_center_logo(frame, logo, logo_w, logo_h, x_offset, y_offset, end_x=1, end_y=1, position=0, width=1920, height=1080):
    if (end_x == 1 and end_y == 1):
        center_w = int(width / 2)
        center_h = int(height / 2)
        if position != 0:
            w_offset = int((width - 2*(x_offset*width))*position)
            center_w = center_w - w_offset
    elif (end_x != 1 and end_y != 1):
        center_w = int(width*x_offset + ((width*end_x - width*x_offset)/2))
        center_h = int(height*y_offset + ((height*end_y - height*y_offset)/2))
        if position != 0:
            w_offset = int((width*end_x - width*x_offset)*position)
            center_w = center_w - w_offset
    elif (end_y != 1):
        center_w = int(width / 2)
        center_h = int(height*y_offset + ((height*end_y - height*y_offset)/2))
        if position != 0:
            w_offset = int((width - 2*(x_offset*width))*position)
            center_w = center_w - w_offset

    if not is_image(logo):
        logo = Image.open(f"resources/img/{logo}")
        
    new_size = (logo_w, logo_h)

    resized_image = logo.resize(new_size)

    logo_origin = (int(center_w - new_size[0] / 2), int(center_h - new_size[1] / 2))

    # Convert cv2 image to PIL image for "paste()"
    frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    frame_copy = frame_pil.copy()

    frame_copy.paste(resized_image, (logo_origin[0], logo_origin[1]), resized_image)

    # Convert PIL image back to cv2 image
    frame = cv2.cvtColor(np.array(frame_copy), cv2.COLOR_RGB2BGR)

    return frame

def calculate_rect_with_msg(msg, font, font_scale, width=1920, height=1080):
    pass

input_video_path = 'opencv_testing/video_2.mp4'
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
font_style = cv2.FONT_HERSHEY_SIMPLEX
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

# 16 9 aspect ratio
#page 1
p1_big_x = 0.36
p1_big_y = 0.4045
p1_home = "Sparta Rotterdam FC"
p1_visiting = "FC Volendam"

p1_small_x = 0.47
p1_small_y = 0.33
p1_small_end_y = 0.4
p1_small_font = 47/22
p1_small_msg = "ALLSVENSKANghghghhg"

#page 2
p2_x = 0.03
p2_end_x = 0.375

p2_small_y = 0.03
p2_small_end_y = 0.065

p2_big_y = 0.081
p2_big_end_y = 0.185

player_y = 0.88
player_end_y = 0.95

#page 3
p3_small_x = 0.35
p3_small_y = 0.51
p3_small_end_y = 0.56

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
        # team vs team rect
        generate_rect(p1_big_x, p1_big_y, text=[p1_home, p1_visiting], font_scale=0.4)
        generate_center_text(frame, p1_home, p1_big_x, p1_big_y, position=0.2) # Positioned centered to the left of rect
        generate_center_text(frame, p1_visiting, p1_big_x, p1_big_y, position=-0.2) # Positioned centered to the right of rect
        frame = generate_center_logo(frame, "allsvenskan.png", 150, 150, p1_big_x, p1_big_y)
        frame = generate_center_logo(frame, "rotterdam.png", 150, 150, p1_big_x, p1_big_y, position=0.4)
        frame = generate_center_logo(frame, "volendam.png", 150, 150, p1_big_x, p1_big_y, position=-0.4)
        # league rect
        p1_small_h = generate_rect(p1_small_x, p1_small_y, end_y=p1_small_end_y, text=[p1_small_msg], font_scale=0.6)
        generate_center_text(frame, p1_small_msg, p1_small_x, p1_small_y, end_y=p1_small_end_y, rect_h=p1_small_h*0.6) # Scaling the font to 60% of rectangle-height
        
    if i > int(duration* 0.08):
        # p2
        # small league rect (top left)
        p2_small_h = generate_rect(p2_x, p2_small_y, p2_end_x, p2_small_end_y)
        generate_center_text(frame, "ALLSVENSKAN",p2_x, p2_small_y, end_x=p2_end_x, end_y=p2_small_end_y, rect_h=p2_small_h*0.75)
        # scoreboard
        p2_big_h = generate_rect(p2_x, p2_big_y, p2_end_x, p2_big_end_y)
        generate_center_text(frame, "05:20", p2_x, p2_big_y, p2_end_x, p2_big_end_y, rect_h=p2_big_h*0.5)
        generate_center_text(frame, "1", p2_x, p2_big_y, p2_end_x, p2_big_end_y, position=0.4, rect_h=p2_big_h*0.6)
        generate_center_text(frame, "2", p2_x, p2_big_y, p2_end_x, p2_big_end_y, position=-0.4, rect_h=p2_big_h*0.6)
        frame = generate_center_logo(frame, "rotterdam.png", 100, 100, p2_x, p2_big_y, p2_end_x, p2_big_end_y, position=0.25)
        frame = generate_center_logo(frame, "volendam.png", 100, 100, p2_x, p2_big_y, p2_end_x, p2_big_end_y, position=-0.25)
    if i > int(duration * 0.4) and i < (duration * 0.7):
        generate_rect(p2_x, player_y, p2_end_x, player_end_y)

    if i > (duration * 0.8):
        # League rect
        p3_small_h = generate_rect(p3_small_x, p3_small_y, end_y=p3_small_end_y)
        generate_center_text(frame, "ALLSVENSKAN", p3_small_x, p3_small_y, end_y=p3_small_end_y, rect_h=p3_small_h*0.75)
        
        # Action performed by player
        generate_rect(p3_x, p3_big_y, end_y=p3_big_end_y, opacity=0)
        generate_center_text(frame, "Sparta Rotterdam FC", p3_x, p3_big_y, end_y=p3_big_end_y, position=-.1)
        frame = generate_center_logo(frame, "rotterdam.png", 75, 75, p3_x, p3_big_y, end_y=p3_big_end_y, position=0.35)
        generate_rect(p3_x, p3_big_end_y, end_y=p3_player_end_y)
        generate_center_text(frame, "Player name name name", p3_x, p3_big_end_y, end_y=p3_player_end_y, position=-.1)
        frame = generate_center_logo(frame, "football.png", 75, 75, p3_x, p3_big_end_y, end_y=p3_player_end_y, position=0.35)

    out.write(frame)
    
cap.release()
out.release()
        