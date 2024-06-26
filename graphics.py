import requests
import os
import cv2
import time
import logging
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageColor
from urllib.parse import urlparse
from utils import run_and_log
from math import sqrt

included_events = ['goal', 'shot', 'yellow card', 'red card', 'penalty']

class GraphicsTemplate:
    def __init__(self):
        self.template_name = None
        self.clip = None
        self.fg_color = None
        self.bg_color = None
        self.border_color = None
        self.text_color = None

    def initialize(self, clip, data):
        try:
            self.template_name = data.get('template', {}).get('name', None)
            self.clip = clip
            self.fg_color = data.get('fg_color', '#ffc300')
            self.bg_color = data.get('bg_color', '#ffc300')
            self.border_color = data.get('border_color', '#ffffff')
            self.text_color = data.get('text_color', '#000000')
            return True
        except Exception:
            return False
        
    def download_and_meta(self, video_w, video_h, fps, is_compilation, platform, graphic_settings, clip_num):
        tpc = time.perf_counter()

        video_h = self.clip.video_height()
        video_w = self.clip.video_width()
        fps = self.clip.frame_rate()
        home_color = graphic_settings.get('home_color')
        visiting_color = graphic_settings.get('visiting_color')
        graphic_template = graphic_settings.get('template')
        graphic_layout = graphic_settings.get('graphic_layout')

        generate_meta = False
        for meta in self.clip.config['clip_meta']:
            action = meta['action']
            if action in included_events:
                generate_meta = True

        if not generate_meta:
            return
        
        create_animated_meta(video_h, video_w, self.clip.config['clip_meta'], self.bg_color, self.text_color, home_color, visiting_color, self.clip.local_file_name, clip_num, graphic_template, graphic_layout, self.clip.aspect_ratio)

def generate_rect(x_offset, y_offset, end_x=1, end_y=1, color=(255, 255, 255), text=[], font_scale=1, grow="", opacity=1):
    global font_style, width, height, frame
    if opacity != 1:
        overlay = frame.copy()
    # If rectangle is centered both horiz. and vert.
    if (end_x == 1 and end_y == 1):
        top_left = int(width * x_offset), int(height * y_offset)
        bottom_right = (int(width - top_left[0]), int(height - top_left[1]))
    # If rectangle is offcenter both horiz. and vert.
    elif (end_x != 1 and end_y != 1):
        top_left = int(width * x_offset), int(height * y_offset)
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
        if grow == "":
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
        elif grow == "left":
            new_top_left[0] = int(top_left[0] - text_width)
            new_bottom_right[0] = bottom_right[0]
        else:
            new_top_left[0] = top_left[0]
            new_bottom_right[0] = int(bottom_right[0] + text_width)

        top_left = tuple(new_top_left)
        bottom_right = tuple(new_bottom_right)
    
    cv2.rectangle(frame, top_left, bottom_right, color, -1)
    
    if opacity != 1:
        cv2.addWeighted(overlay, opacity, frame, 1 - opacity, 0, frame)

    return top_left, bottom_right, bottom_right[1]-top_left[1] # Return top_left, bottom_right and height of rect.

def generate_center_text(text, x_offset, y_offset, end_x=1, end_y=1, position=0, color=(0,0,0), thickness=2, rect_h=0, font_scale=1):
    global font_style, frame, height, width
    
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

def generate_center_logo(logo, logo_w, logo_h, x_offset, y_offset, end_x=1, end_y=1, position=0, keepRatio=False):
    global width, height, frame
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

    if keepRatio:
        # Not working, ValueError: use 4-item box
        resized_image = logo.thumbnail((new_size)) 
    else:
        resized_image = logo.resize(new_size)

    logo_origin = (int(center_w - new_size[0] / 2), int(center_h - new_size[1] / 2))

    # Convert cv2 image to PIL image for "paste()"
    frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    frame_copy = frame_pil.copy()

    frame_copy.paste(resized_image, (logo_origin[0], logo_origin[1]), resized_image)

    # Convert PIL image back to cv2 image
    frame = cv2.cvtColor(np.array(frame_copy), cv2.COLOR_RGB2BGR)

    return frame

def generate_diamond(x_offset, y_offset, length_offset, rotation=45, color=(255, 255, 255)):
    global width, height, frame
    # Calculate position for polygon-center with video's widtg and height
    center_x = x_offset * width
    center_y = y_offset * height
    length = length_offset * height
    
    top_left = (center_x - length, center_y - length)
    bottom_right = (center_x + length, center_y + length)

    # Calculate vertices for polygon
    vertices = [(center_x + length, center_y), (center_x, center_y + length), (center_x - length, center_y), (center_x, center_y - length)]

    # Convert frame for PIL-draw usage
    frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    frame_copy = frame_pil.copy()
    draw = ImageDraw.Draw(frame_copy)

    draw.polygon(vertices, fill=color)

    # Convert frame for OpenCV usage
    frame = cv2.cvtColor(np.array(frame_copy), cv2.COLOR_RGB2BGR)

    # Return frame with polygon and corner positions og element, for further use when placing logo/icons
    return frame, top_left, bottom_right


def is_image(var):
    return isinstance(var, Image.Image)

def get_img(url: str) -> Image or None:
    response = requests.get(url)

    if response.status_code == 200:
        parsed_url = urlparse(url)
        
        filename = os.path.basename(parsed_url.path)
        folder_path = 'images'
        save_path = os.path.join(folder_path, filename)
        
        with open(save_path, 'wb') as f:
            f.write(response.content)
        with Image.open(save_path) as img:
            out = img.copy()
        
        os.remove(save_path)
        return out

def get_img_local(image_name):
    folder_path = 'resources/img'
    image_path = os.path.join(folder_path, image_name)

    with Image.open(image_path) as img:
        out = img.copy()
    
    return out

def hex_to_bgr(hex):
    rgb = list(ImageColor.getcolor(hex, "RGB"))
    rgb[0], rgb[-1] = rgb[-1], rgb[0]
    bgr = tuple(rgb)
    return bgr

def get_action_message_and_icon(meta, language='EN'): 
    team_logo_url = meta['home_logo_url']
    score = meta['score']
    player_name = meta['player_name']

    if language == 'EN':
        if meta['action'] == 'shot':
            icon = get_img_local('icons/shot_icon.png')
            msg = 'Shot at goal'
        elif meta['action'] == 'goal':
            icon = get_img_local('icons/goal_icon.png')
            msg = 'Goal'
        elif meta['action'] == 'yellow card':
            icon = get_img_local('icons/yellow_icon.png')
            msg = 'Yellow card'
        elif meta['action'] == 'red card':
            icon = get_img_local('icons/red_icon.png')
            msg = 'Red card'
        elif meta['action'] == 'penalty':
            icon = get_img_local('icons/penalty_icon.png')
        else:
            icon = get_img_local('ball_icon.png')
            msg = 'Missing action'

        return icon, msg
    
width = 1920
height = 1080
frame = np.zeros((height, width, 3), dtype=np.uint8)
font_style = cv2.FONT_HERSHEY_SIMPLEX

def create_animated_meta(video_h, video_w, clip_meta, bg_color, text_color, home_color, visiting_color, local_file_name, clip_num, graphic_template, graphic_layout, aspect_ratio=[16, 9], fps=25.0):
    global frame, width, height, font_style
    for i, meta in enumerate(clip_meta):
        # Initialize video capture 
        cap = cv2.VideoCapture(local_file_name)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        duration = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        output_filename = f'video/{clip_num}_meta.mp4'
        
        if os.path.exists(output_filename):
            os.remove(output_filename)
            print(f"Existing {output_filename} deleted successfully.")

        out = cv2.VideoWriter(output_filename, fourcc, fps, (width, height))
        
        home_logo_url = meta['home_logo_url']
        home_name = meta['home_name']
        home_ini = meta['home_initials']
        home_color1 = hex_to_bgr(home_color[0])
        home_color2 = hex_to_bgr(home_color[1])

        visiting_logo_url = meta['visiting_logo_url']
        visiting_name = meta['visiting_name']
        visiting_ini = meta['visiting_initials']
        visiting_color1 = hex_to_bgr(visiting_color[0])
        visiting_color2 = hex_to_bgr(visiting_color[1])
        
        league_logo_url = meta['league_logo_url']
        league_name = meta['league_name']
        icon, msg = get_action_message_and_icon(meta)
        player_logo_url = "icons/player_icon.png"
        player_name = meta['player_name']
        score = meta['score']
        game_time = meta['time']

        # Dynamic sizes
        if aspect_ratio == [16, 9] or aspect_ratio is None:
            if graphic_template == 'rectangle':
                aspect_ratio = [16, 9]
                
                bg_color_graphic = hex_to_bgr(bg_color) 
                bg_color_white = hex_to_bgr("#FFFFFF")
                bg_color_black = hex_to_bgr("#343434")
                text_color = hex_to_bgr(text_color)
                text_color_black = hex_to_bgr("#343434")

                # Introduction
                # y-offset
                in_y_start = 0.78
                in_y_end = 0.85

                # x-offset
                in_team1_logo_offset  = -0.04
                in_team1_name_start = 0.45
                in_team1_name_end = 0.46
                in_team1_color_end = 0.47
                
                in_score_end = 0.53

                in_team2_color_end = 0.54
                in_team2_name_end = 0.55
                in_team2_logo_offset = 0.04

                in_league_start = 0.49
                in_league_end = 0.51

                # Scoreboard
                # y-offset
                sc_y_start = 0.055
                sc_y_end = 0.1
                sc_y_league_end = 0.9
                sc_y_time_end = 0.145

                # x-offset
                sc_team1_logo_start = 0.04
                sc_team1_logo_end = 0.065 #0.025
                sc_team1_color_end = 0.068
                sc_team1_name_end = 0.113
                sc_team1_score_end = 0.137

                sc_team2_score_start = 0.198
                sc_team2_score_end = 0.223
                sc_team2_name_end = 0.271
                sc_team2_color_start = 0.268
                sc_team2_logo_end = 0.295

                # Action
                # y-offset
                ac_y_start = 0.85
                ac_y_end = 0.9
                ac_msg_y_end = 0.93
                # x-offset
                ac_team_color_start = 0.04
                ac_team_color_end = 0.043
                ac_player_end = 0.068
                ac_name_end = 0.072
                ac_action_offset = 0.025 

                ac_icon_height = int(0.048*height*0.9)
                ac_icon_width = int(0.027*width*0.9)

                # Icons !! Aspect ratio is not kept !!
                if "j1" in league_logo_url or "allsvenskan" in league_logo_url:
                    league_height = int(0.2*height - 0.125*height)
                    league_width = int(0.2*width - 0.16*width)
                else:
                    league_height = int(0.2*width - 0.16*width)
                    league_width = int(0.2*width - 0.16*width)
                
                sc_team1_logo_dim = int((sc_team1_logo_end*width - sc_team1_logo_start*width)*0.8)
                sc_team2_logo_dim = int((sc_team1_logo_end*width - sc_team1_logo_start*width)*0.8)

                if graphic_layout == "center":
                    sc_middle_offset = 0.332
                    sc_team1_logo_start += sc_middle_offset
                    sc_team1_logo_end += sc_middle_offset
                    sc_team1_color_end += sc_middle_offset
                    sc_team1_name_end += sc_middle_offset
                    sc_team1_score_end +=sc_middle_offset

                    sc_team2_score_start += sc_middle_offset
                    sc_team2_score_end += sc_middle_offset
                    sc_team2_name_end += sc_middle_offset
                    sc_team2_color_start += sc_middle_offset
                    sc_team2_logo_end +=  sc_middle_offset

                    ac_team_color_start += sc_middle_offset
                    ac_team_color_end += sc_middle_offset
                    ac_player_end += sc_middle_offset
                    ac_name_end += sc_middle_offset

            elif graphic_template == 'diamond':
                aspect_ratio = [16, 9]
                # Color-template
                bg_color_graphic = hex_to_bgr(bg_color)
                bg_color_black = hex_to_bgr("#343434")
                bg_color_white = hex_to_bgr("#FFFFFF")
                text_color_graphic = hex_to_bgr(text_color)
                text_color_white = hex_to_bgr("#FFFFFF")

                # Scoreboard
                sc_league_center_x = 0.045
                sc_league_center_y = 0.1
                sc_league_length = 0.055

                if "allsvenskan" in league_logo_url:
                    sc_league_height = int(0.07*height)
                    sc_league_width = int(0.03*width)
                elif "j1" in league_logo_url:
                    sc_league_height = int(0.06*height)
                    sc_league_width = int(0.03*width)
                else:
                    sc_league_height = int(0.063*height)
                    sc_league_width = int(0.035*width)

                sc_team1_name_start = sc_league_center_x
                sc_team1_name_end = 0.13
                sc_team1_color_end = 0.135
                sc_score_end = 0.205
                sc_team2_color_end = 0.21
                sc_team2_name_end = 0.285

                # Introduction
                in_league_center_x = 0.5
                in_league_center_y = 0.83
                in_league_length = 0.07

                if "allsvenskan" in league_logo_url:
                    in_league_height = int(0.08*height)
                    in_league_width = int(0.035*width)
                elif "j1" in league_logo_url:
                    in_league_height = int(0.072*height)
                    in_league_width = int(0.035*width)
                else:
                    in_league_height = int(0.082*height)
                    in_league_width = int(0.046*width)

                in_team1_name_start = in_league_center_x - 0.04
                in_team1_name_end = in_league_center_x
                in_team1_color_offset = -0.005
                in_team1_score_offset = -0.04
                in_team1_logo_offset = -0.04

                in_team2_name_start = in_league_center_x 
                in_team2_name_end = in_team2_name_start + 0.04
                in_team2_color_offset = 0.005
                in_team2_score_offset = 0.04
                in_team2_logo_offset = 0.04

                in_league_name_offset = 0.04

                # Very simple and inefficient way to maintain aspect ratio of logos when resizing
                potrait_logo = ["tokyo", "urawa", "volen", "fortuna"] 
                if any(x in home_logo_url for x in potrait_logo):
                    in_team1_height = int(0.055*height)
                    in_team1_width = int(0.026*width)
                else:
                    in_team1_height = int(0.054*height)
                    in_team1_width = int(0.03*width)

                if any(x in visiting_logo_url for x in potrait_logo):
                    in_team2_height = int(0.055*height)
                    in_team2_width = int(0.026*width)
                else:
                    in_team2_height = int(0.054*height)
                    in_team2_width = int(0.03*width)

                # Action
                ac_team_center_x = 0.045
                ac_team_center_y = 0.9
                ac_team_length = 0.055

                ac_name_y_start = ac_team_center_y
                ac_name_y_end = ac_team_center_y + ac_team_length
                ac_name_start = ac_team_center_x
                ac_name_end = ac_name_start + 0.02

                ac_action_y_start = ac_team_center_y - ac_team_length/2
                ac_action_y_end = ac_team_center_y
                ac_action_start = ac_team_center_x
                ac_action_end = ac_action_start + 0.08

                if graphic_layout == "center":
                    sc_middle_offset = 0.3203125
                    sc_league_center_x += sc_middle_offset
                    sc_team1_name_start = sc_league_center_x
                    sc_team1_name_end +=  sc_middle_offset
                    sc_team1_color_end += sc_middle_offset
                    sc_score_end +=       sc_middle_offset
                    sc_team2_color_end += sc_middle_offset
                    sc_team2_name_end +=  sc_middle_offset
                    
                    ac_middle_offset = sc_middle_offset
                    ac_team_center_x += ac_middle_offset
                    ac_name_start = ac_team_center_x
                    ac_name_end = ac_name_start + 0.06
                    ac_action_start = ac_team_center_x
                    ac_action_end = ac_action_start + 0.06

        elif aspect_ratio == [9, 16]:
            if graphic_template == 'diamond':
                bg_color_graphic = hex_to_bgr(bg_color)
                bg_color_black = hex_to_bgr("#343434")
                bg_color_white = hex_to_bgr("#FFFFFF")
                text_color_graphic = hex_to_bgr(text_color)
                text_color_white = hex_to_bgr("#FFFFFF")

                # Scoreboard
                sc_league_center_x = 0.172
                sc_league_center_y = 0.095
                sc_league_length = 0.04

                if "allsvenskan" in league_logo_url:
                    sc_league_height = int(0.048*height)
                    sc_league_width = int(0.08*width)
                elif "j1" in league_logo_url:
                    sc_league_height = int(0.042*height)
                    sc_league_width = int(0.067*width)
                else:
                    sc_league_height = int(0.044*height)
                    sc_league_width = int(0.08*width)
         
                sc_team1_name_start = sc_league_center_x
                sc_team1_name_end = 0.355
                sc_team1_color_end = 0.366
                sc_score_end = 0.518
                sc_team2_color_end = 0.529
                sc_team2_name_end = 0.712

                # Introduction
                if "allsvenskan" in league_logo_url:
                    in_league_height = int(0.08*height)
                    in_league_width = int(0.035*width)
                elif "j1" in league_logo_url:
                    in_league_height = int(0.072*height)
                    in_league_width = int(0.035*width)
                else:
                    in_league_height = int(0.082*height)
                    in_league_width = int(0.046*width)


                in_team1_center_x = sc_league_center_x
                in_team1_center_y = 0.788
                in_team1_length = sc_league_length

                in_team1_y_start = in_team1_center_y - in_team1_length
                in_team1_y_end = in_team1_center_y
                in_team1_name_start = in_team1_center_x
                in_team1_name_end = in_team1_center_x + 0.04
                in_team1_color_offset = 0.01
                in_team1_score_offset = 0.07
                
                in_team2_center_x = 0.827
                in_team2_center_y = 0.869
                in_team2_length = sc_league_length

                in_team2_y_start = in_team2_center_y
                in_team2_y_end = in_team2_center_y + sc_league_length
                in_team2_name_end = in_team2_center_x 
                in_team2_name_start = in_team2_name_end - 0.04
                in_team2_color_offset = -0.01
                in_team2_score_offset = -0.07

                in_league_y_start = 0.808
                in_league_y_end = in_league_y_start + sc_league_length
                in_league_name_start = 0.474
                in_league_name_end = 0.509
                
                # Very simple and inefficient way to maintain aspect ratio of logos when resizing
                if "volen" in home_logo_url:
                    in_team1_width = int(0.07*width)
                    in_team1_height = int(0.044*height)
                elif "psv" in home_logo_url:
                    in_team1_width = int(0.101*width)
                    in_team1_height = int(0.047*height)
                elif "rot" in home_logo_url and "kashima" in home_logo_url:
                    in_team1_width = int(0.088*width)
                    in_team1_height = int(0.05*height)
                else:
                    in_team1_width = int(0.066*width)
                    in_team1_height = int(0.0463*height)

                if "volen" in visiting_logo_url:
                    in_team2_width = int(0.07*width)
                    in_team2_height = int(0.044*height)
                elif "psv" in visiting_logo_url:
                    in_team2_width = int(0.101*width)
                    in_team2_height = int(0.047*height)
                elif "rot" in visiting_logo_url or "kashima" in visiting_logo_url:
                    in_team2_width = int(0.088*width)
                    in_team2_height = int(0.05*height)
                else:
                    in_team2_width = int(0.066*width)
                    in_team2_height = int(0.0463*height)

                # Action
                ac_team_center_x = 0.827
                ac_team_center_y = 0.869
                ac_team_length = sc_league_length

                ac_name_y_start = ac_team_center_y
                ac_name_y_end = ac_team_center_y + ac_team_length
                ac_name_end = ac_team_center_x
                ac_name_start = ac_name_end - 0.02

                ac_action_y_start = ac_team_center_y - ac_team_length/2
                ac_action_y_end = ac_team_center_y
                ac_action_end = ac_team_center_x
                ac_action_start = ac_action_end + 0.04

                if graphic_layout == "center":
                    sc_middle_offset = 0.07685185185
                    sc_league_center_x += sc_middle_offset
                    sc_team1_name_start = sc_league_center_x
                    sc_team1_name_end +=  sc_middle_offset
                    sc_team1_color_end += sc_middle_offset
                    sc_score_end +=       sc_middle_offset
                    sc_team2_color_end += sc_middle_offset
                    sc_team2_name_end +=  sc_middle_offset
                    
                    ac_middle_offset = -sc_middle_offset
                    ac_team_center_x += ac_middle_offset
                    ac_name_end = ac_team_center_x
                    ac_name_start = ac_name_end - 0.02
                    ac_action_end = ac_team_center_x
                    ac_action_start = ac_action_end - 0.04
        else:
            raise ValueError(f'Invalid aspect ratio entered: {aspect_ratio}.')
        
        i = 1
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            i += 1
            if graphic_template == 'rectangle':
            # Scoreboard
                if i <= int(duration):
                    # Home team
                    generate_rect(sc_team1_logo_start, sc_y_start, sc_team1_logo_end, sc_y_end, bg_color_graphic) # Logo container
                    generate_rect(sc_team1_color_end, sc_y_start, sc_team1_name_end, sc_y_end, bg_color_graphic) # Name container
                    generate_rect(sc_team1_logo_end, sc_y_start, sc_team1_color_end, sc_y_end - (sc_y_end - sc_y_start)/2, home_color1) # Color1 rect
                    generate_rect(sc_team1_logo_end, sc_y_end - (sc_y_end - sc_y_start)/2, sc_team1_color_end, sc_y_end, home_color2) # Color2 rect
                    generate_rect(sc_team1_name_end, sc_y_start, sc_team1_score_end, sc_y_end, bg_color_white) # Score container

                    generate_rect(sc_team1_score_end, sc_y_start, sc_team2_score_start, sc_y_end, bg_color_white) # League container
                    generate_rect(sc_team2_score_end, sc_y_end, sc_team2_logo_end, sc_y_time_end, bg_color_black, opacity=0.11) # Time container

                    # Visiting team
                    generate_rect(sc_team2_score_start, sc_y_start, sc_team2_score_end, sc_y_end, bg_color_white) # Score
                    generate_rect(sc_team2_score_end, sc_y_start, sc_team2_color_start, sc_y_end, bg_color_graphic) # Name
                    generate_rect(sc_team2_color_start, sc_y_start, sc_team2_name_end, sc_y_end - (sc_y_end - sc_y_start)/2, visiting_color1) # Color1
                    generate_rect(sc_team2_color_start, sc_y_end - (sc_y_end - sc_y_start)/2, sc_team2_name_end, sc_y_end, visiting_color2) # Color2
                    generate_rect(sc_team2_name_end, sc_y_start, sc_team2_logo_end, sc_y_end, bg_color_graphic) # Logo
                    
                    # Logo
                    frame = generate_center_logo(league_logo_url, league_width, league_height, sc_team1_score_end, sc_y_start, sc_team2_score_start, sc_y_end) # League
                    frame = generate_center_logo(home_logo_url, sc_team1_logo_dim, sc_team1_logo_dim, sc_team1_logo_start, sc_y_start, sc_team1_logo_end, sc_y_end) # Home team
                    frame = generate_center_logo(visiting_logo_url,sc_team2_logo_dim, sc_team2_logo_dim,sc_team2_name_end, sc_y_start,sc_team2_logo_end, sc_y_end) # Visiting team

                    # Text
                    generate_center_text(home_ini, sc_team1_color_end, sc_y_start, sc_team1_name_end, sc_y_end, color=text_color, font_scale=0.8) # Home initials
                    generate_center_text(score[0], sc_team1_name_end, sc_y_start, sc_team1_score_end, sc_y_end, color=text_color_black) # Home score
                    generate_center_text(visiting_ini, sc_team2_score_end, sc_y_start, sc_team2_color_start, sc_y_end, color=text_color, font_scale=0.8) # Visiting intials
                    generate_center_text(score[2], sc_team2_score_start, sc_y_start, sc_team2_score_end, sc_y_end, color=text_color_black) # Visiting score
                    generate_center_text(game_time, sc_team2_score_end, sc_y_end, sc_team2_logo_end, sc_y_time_end, color=bg_color_white) # Game time

                if i > int(duration * 0.025) and i < int(duration * 0.125):
                    # Intro
                    name1_topleft, name1_bottomright, rect_height = generate_rect(in_team1_name_start, in_y_start, in_team1_name_end, in_y_end, bg_color_graphic, text=[home_name, visiting_name], grow="left", font_scale=0.5) # Name
                    in_team1_logo_start = (name1_topleft[0]/width)+in_team1_logo_offset
                    in_team1_logo_end = name1_topleft[0]/width
                    generate_rect(in_team1_logo_start, in_y_start, in_team1_logo_end, in_y_end, bg_color_graphic) # Logo
                    generate_rect(in_team1_name_end, in_y_start, in_team1_color_end, in_y_end - (in_y_end - in_y_start)/2, home_color1) # Color1
                    generate_rect(in_team1_name_end, in_y_end - (in_y_end - in_y_start)/2, in_team1_color_end, in_y_end, home_color2) # Color2
                    
                    generate_rect(in_team1_color_end, in_y_start, in_score_end, in_y_end, bg_color_white) # Score
                    
                    generate_rect(in_score_end, in_y_start, in_team2_color_end, in_y_end - (in_y_end - in_y_start)/2, visiting_color1) # Color1
                    generate_rect(in_score_end, in_y_end - (in_y_end - in_y_start)/2, in_team2_color_end, in_y_end, visiting_color2) # Color2
                    name2_topleft, name2_bottomright, rect_height = generate_rect(in_team2_color_end, in_y_start, in_team2_name_end, in_y_end, bg_color_graphic, text=[home_name, visiting_name], grow="right", font_scale=0.5) # Name
                    in_team2_logo_start = name2_bottomright[0]/width
                    in_team2_logo_end = (name2_bottomright[0]/width)+in_team2_logo_offset
                    generate_rect(in_team2_logo_start, in_y_start, in_team2_logo_end, in_y_end, bg_color_graphic) # Logo

                    league_topleft, league_bottomright, rect2_height = generate_rect(in_league_start, in_y_end, in_league_end, sc_y_league_end, bg_color_graphic, text=[league_name], font_scale=0.5) # League
                    
                    # Logo
                    in_team_logo_dim = int((in_team2_logo_end*width - in_team2_logo_start*width)*0.8) # Logo height and width equal 80% container height
                    frame = generate_center_logo(home_logo_url, in_team_logo_dim, in_team_logo_dim, in_team1_logo_start, in_y_start, in_team1_logo_end, in_y_end) # Home logo
                    frame = generate_center_logo(visiting_logo_url, in_team_logo_dim, in_team_logo_dim, in_team2_logo_start, in_y_start, in_team2_logo_end, in_y_end) # Visiting logo

                    # Text
                    rect_height = rect_height*0.4 # Scale font to container height
                    rect2_height = rect2_height*0.4
                    generate_center_text(home_name, name1_topleft[0]/width, in_y_start, name1_bottomright[0]/width, in_y_end, rect_h=rect_height, color=text_color) # Home name
                    generate_center_text(visiting_name, name2_topleft[0]/width, in_y_start, name2_bottomright[0]/width, in_y_end, rect_h=rect_height, color=text_color) # Visiting name
                    generate_center_text(score, in_team1_color_end, in_y_start, in_score_end, in_y_end, color=text_color_black, rect_h=rect_height) # Score
                    generate_center_text(league_name, league_topleft[0]/width, in_y_end, league_bottomright[0]/width, sc_y_league_end, color=bg_color_white, rect_h=rect2_height) # League name

                if i > int(duration*0.3) and i < int(duration*0.6):
                    # Action
                    generate_rect(ac_team_color_start, ac_y_start, ac_team_color_end, ac_y_end - (ac_y_end - ac_y_start)/2, color=home_color1) # Jersey color1
                    generate_rect(ac_team_color_start, ac_y_end - (ac_y_end - ac_y_start)/2, ac_team_color_end, ac_y_end, color=home_color2) # Jersey color2
                    generate_rect(ac_team_color_end, ac_y_start, ac_player_end, ac_y_end, color=bg_color_graphic) # Player icon container
                    player_topleft, player_bottomright, rect_h = generate_rect(ac_player_end, ac_y_start, ac_name_end, ac_y_end, text=[player_name], color=bg_color_graphic, grow="right", font_scale=0.5) # Dynamic container of player name
                    generate_rect(player_bottomright[0]/width, ac_y_start, player_bottomright[0]/width+ac_action_offset, ac_y_end,color=bg_color_white) # Action icon container
                    generate_rect(player_topleft[0]/width, ac_y_end, player_bottomright[0]/width, ac_msg_y_end, color=bg_color_graphic, opacity=0.11) # Action message container

                    frame = generate_center_logo(player_logo_url, ac_icon_width, ac_icon_height, ac_team_color_end, ac_y_start, ac_player_end, ac_y_end) # Player icon
                    frame = generate_center_logo(icon, ac_icon_width, ac_icon_height, player_bottomright[0]/width, ac_y_start, player_bottomright[0]/width+ac_action_offset, ac_y_end) # Action icon

                    generate_center_text(player_name, player_topleft[0]/width, ac_y_start, player_bottomright[0]/width, ac_y_end, color=text_color) # Player name
                    generate_center_text(msg, player_topleft[0]/width, ac_y_end, player_bottomright[0]/width, ac_msg_y_end, color=bg_color_white, font_scale=0.7) # Action message
                    
            elif graphic_template == 'diamond':
                # Scoreboard
                if i <= (duration):
                    # Generate diamond, return posistion of diamond for placing logo on-top
                    frame, sc_league_topleft, sc_league_bottomright = generate_diamond(sc_league_center_x, sc_league_center_y, sc_league_length, color=bg_color_black)

                    # Height of graphics start from peak of diamond to middle of diamond
                    sc_y_start = sc_league_topleft[1]/height
                    sc_y_end = sc_league_center_y

                    # Scoreboard team 1
                    generate_rect(sc_team1_name_start, sc_y_start, sc_team1_name_end, sc_y_end, color=bg_color_black)
                    generate_rect(sc_team1_name_end, sc_y_start, sc_team1_color_end, sc_y_end - (sc_y_end - sc_y_start)/2, color=home_color1)
                    generate_rect(sc_team1_name_end, sc_y_end - (sc_y_end - sc_y_start)/2, sc_team1_color_end, sc_y_end, color=home_color2)

                    # Score
                    generate_rect(sc_team1_color_end, sc_y_start, sc_score_end, sc_y_end, color=bg_color_graphic)
                    
                    # Scoreboard team 2
                    generate_rect(sc_score_end, sc_y_start, sc_team2_color_end, sc_y_end - (sc_y_end - sc_y_start)/2, color=visiting_color1)
                    generate_rect(sc_score_end, sc_y_end - (sc_y_end - sc_y_start)/2, sc_team2_color_end, sc_y_end, color=visiting_color2)
                    generate_rect(sc_team2_color_end, sc_y_start, sc_team2_name_end, sc_y_end, color=bg_color_black)
                 
                    # Draw logo
                    frame = generate_center_logo(league_logo_url, sc_league_width, sc_league_height, sc_league_center_x, sc_league_center_y, sc_league_center_x, sc_league_center_y)
                    
                    # Draw text 
                    generate_center_text(home_ini, sc_team1_name_start, sc_y_start, sc_team1_name_end, sc_y_end, color=text_color_white)
                    generate_center_text(score, sc_team1_color_end, sc_y_start, sc_score_end, sc_y_end, color=text_color_graphic)
                    generate_center_text(visiting_ini, sc_team2_color_end, sc_y_start, sc_team2_name_end, sc_y_end, color=text_color_white)

                # Introduction
                if i > int(duration * 0.025) and i < int(duration * 0.125):
                    if aspect_ratio == [16, 9]:
                        # League diamond container
                        frame, _, in_league_bottomright = generate_diamond(in_league_center_x, in_league_center_y, in_league_length, color=bg_color_black)

                        # Team1 begins from middle to bottom of diamond in y-axis
                        in_team1_y_start = in_league_center_y
                        in_team1_y_end = in_league_bottomright[1]/height

                        # Introduction team1
                        name1_topleft, name1_bottomright, _ = generate_rect(in_team1_name_start, in_team1_y_start, in_team1_name_end, in_team1_y_end, color=bg_color_black, text=[home_name, visiting_name], grow='left', font_scale=0.5)
                        in_team1_color_end = name1_topleft[0]/width + in_team1_color_offset # Top_left of team's color is offset to top_left of team's name
                        generate_rect(in_team1_color_end, in_team1_y_start, name1_topleft[0]/width, in_team1_y_end - (in_team1_y_end - in_team1_y_start)/2, color=home_color1)
                        generate_rect(in_team1_color_end, in_team1_y_end - (in_team1_y_end - in_team1_y_start)/2, name1_topleft[0]/width, in_team1_y_end, color=home_color2)
                        in_team1_score_end = in_team1_color_end + in_team1_score_offset # Move top_left of team's score according to new position of team1's color
                        generate_rect(in_team1_score_end, in_team1_y_start, in_team1_color_end, in_team1_y_end, color=bg_color_graphic)
                        in_team1_logo_end = in_team1_score_end + in_team1_logo_offset # Repeat of above, for logo
                        generate_rect(in_team1_logo_end, in_team1_y_start, in_team1_score_end, in_team1_y_end, color=bg_color_black)

                        # Team2 begins from top to middle of diamond in y-axis
                        in_team2_y_start = in_league_center_y - in_league_length
                        in_team2_y_end = in_league_center_y

                        # Introduction team2
                        name2_topleft, name2_bottomright, _ =  generate_rect(in_team2_name_start, in_team2_y_start, in_team2_name_end, in_team2_y_end, color=bg_color_black, text=[home_name, visiting_name], grow='right', font_scale=0.5)
                        in_team2_color_end = name2_bottomright[0]/width + in_team2_color_offset
                        generate_rect(name2_bottomright[0]/width, in_team2_y_start, in_team2_color_end, in_team2_y_end - (in_team2_y_end - in_team2_y_start)/2, color=visiting_color1)
                        generate_rect(name2_bottomright[0]/width, in_team2_y_end - (in_team2_y_end - in_team2_y_start)/2, in_team2_color_end, in_team2_y_end, color=visiting_color2)
                        in_team2_score_end = in_team2_color_end + in_team2_score_offset
                        generate_rect(in_team2_color_end, in_team2_y_start, in_team2_score_end, in_team2_y_end, color=bg_color_graphic)
                        in_team2_logo_end = in_team2_score_end + in_team2_logo_offset
                        generate_rect(in_team2_score_end, in_team2_y_start, in_team2_logo_end, in_team2_y_end, color=bg_color_black)
                        
                        # Introduction league
                        league_name_topleft, league_name_bottomright, _ = generate_rect(in_league_bottomright[0]/width, in_league_center_y + in_league_length/2, in_league_bottomright[0]/width + in_league_name_offset, in_league_bottomright[1]/height, color=bg_color_black, text=[league_name], grow='right', font_scale=0.5)

                        # Draw logos 
                        frame = generate_center_logo(league_logo_url, in_league_width, in_league_height, in_league_center_x, in_league_center_y, in_league_center_x, in_league_center_y)
                        frame = generate_center_logo(home_logo_url, in_team1_width, in_team1_height, in_team1_logo_end, in_team1_y_start, in_team1_score_end, in_team1_y_end)
                        frame = generate_center_logo(visiting_logo_url, in_team2_width, in_team2_height, in_team2_score_end, in_team2_y_start, in_team2_logo_end, in_team2_y_end)

                        # Draw text
                        generate_center_text(home_name, name1_topleft[0]/width, in_team1_y_start, name1_bottomright[0]/width, in_team1_y_end, color=text_color_white, font_scale=1.2)
                        generate_center_text(visiting_name, name2_topleft[0]/width, in_team2_y_start, name2_bottomright[0]/width, in_team2_y_end, color=text_color_white, font_scale=1.2)
                        generate_center_text(score[0], in_team1_color_end, in_team1_y_start, in_team1_score_end, in_team1_y_end, color=text_color_graphic, thickness=3)
                        generate_center_text(score[-1], in_team2_color_end, in_team2_y_start, in_team2_score_end, in_team2_y_end, color=text_color_graphic, thickness=3)
                        generate_center_text(league_name, league_name_topleft[0]/width, league_name_topleft[1]/height, league_name_bottomright[0]/width, league_name_bottomright[1]/height, color=text_color_white, font_scale=0.8)
                    elif aspect_ratio == [9, 16]:
                        frame, _, _ = generate_diamond(in_team1_center_x, in_team1_center_y, in_team1_length, color=bg_color_black)
                        frame, _, _ = generate_diamond(in_team2_center_x, in_team2_center_y, in_team2_length, color=bg_color_black)

                        name1_topleft, name1_bottomright, _ = generate_rect(in_team1_name_start, in_team1_y_start, in_team1_name_end, in_team1_y_end, color=bg_color_black, text=[home_name, visiting_name], grow='right', font_scale=0.5)
                        in_team1_color_start = name1_bottomright[0]/width
                        in_team1_color_end = in_team1_color_start + in_team1_color_offset
                        generate_rect(in_team1_color_start, in_team1_y_start, in_team1_color_end, in_team1_y_end - (in_team1_y_end - in_team1_y_start)/2, color=home_color1)
                        generate_rect(in_team1_color_start, in_team1_y_end - (in_team1_y_end - in_team1_y_start)/2, in_team1_color_end, in_team1_y_end, color=home_color2)
                        generate_rect(in_team1_color_end, in_team1_y_start, in_team1_color_end+in_team1_score_offset, in_team1_y_end, color=bg_color_graphic)

                        league_topleft, league_bottomright, _ = generate_rect(in_league_name_start, in_league_y_start, in_league_name_end, in_league_y_end, color=bg_color_black, text=[league_name], opacity=0.11, font_scale=0.5)

                        name2_topleft, name2_bottomright, _ = generate_rect(in_team2_name_start, in_team2_y_start, in_team2_name_end, in_team2_y_end, color=bg_color_black, text=[home_name,visiting_name], grow='left', font_scale=0.5)
                        in_team2_color_start = name2_topleft[0]/width + in_team2_color_offset
                        in_team2_color_end = name2_topleft[0]/width
                        generate_rect(in_team2_color_start, in_team2_y_start, in_team2_color_end, in_team2_y_end - (in_team2_y_end - in_team2_y_start)/2, color=visiting_color1)
                        generate_rect(in_team2_color_start, in_team2_y_end - (in_team2_y_end - in_team2_y_start)/2, in_team2_color_end, in_team2_y_end, color=visiting_color2)
                        generate_rect(in_team2_color_start+in_team2_score_offset, in_team2_y_start, in_team2_color_start, in_team2_y_end, color=bg_color_graphic)

                        frame = generate_center_logo(home_logo_url, in_team1_width, in_team1_height, in_team1_center_x, in_team1_center_y, in_team1_center_x, in_team1_center_y)
                        frame = generate_center_logo(visiting_logo_url, in_team2_width, in_team2_height, in_team2_center_x, in_team2_center_y, in_team2_center_x, in_team2_center_y)

                        generate_center_text(home_name, name1_topleft[0]/width, in_team1_y_start, name1_bottomright[0]/width, in_team1_y_end, color=text_color_white, font_scale=0.8)
                        generate_center_text(visiting_name, name2_topleft[0]/width, in_team2_y_start, name2_bottomright[0]/width, in_team2_y_end, color=text_color_white, font_scale=0.8)
                        generate_center_text(league_name, league_topleft[0]/width, in_league_y_start, league_bottomright[0]/width, in_league_y_end, color=text_color_white, font_scale=0.8)
                        generate_center_text(score[0], in_team1_color_end, in_team1_y_start, in_team1_color_end+in_team1_score_offset, in_team1_y_end, color=text_color_graphic, font_scale=0.8)
                        generate_center_text(score[-1], in_team2_color_end+in_team2_score_offset, in_team2_y_start, in_team2_color_start, in_team2_y_end, color=text_color_graphic, font_scale=0.8)
                # Action
                if i > int(duration*0.3) and i < int(duration*0.6):
                    if aspect_ratio == [16, 9]:
                        action_topleft, action_bottomright, _ = generate_rect(ac_action_start, ac_action_y_start, ac_action_end, ac_action_y_end, color=bg_color_graphic, text=[msg], grow='right', font_scale=0.5)
                        frame, ac_team_topleft, ac_team_bottomright = generate_diamond(ac_team_center_x, ac_team_center_y, ac_team_length, color=bg_color_black)
                        player_topleft, player_bottomright, _ = generate_rect(ac_name_start, ac_name_y_start, ac_name_end, ac_name_y_end, color=bg_color_black, text=[player_name], grow='right', font_scale=0.5)

                        frame = generate_center_logo(home_logo_url, in_team1_width, in_team1_height, ac_team_center_x, ac_team_center_y, ac_team_center_x, ac_team_center_y)

                        generate_center_text(player_name, player_topleft[0]/width, player_topleft[1]/height, player_bottomright[0]/width, player_bottomright[1]/height, color=text_color_white)
                        generate_center_text(msg, action_topleft[0]/width, action_topleft[1]/height, action_bottomright[0]/width, action_bottomright[1]/height, color=text_color_graphic, font_scale=0.7)
                    elif aspect_ratio == [9, 16]:
                        action_topleft, action_bottomright, _ = generate_rect(ac_action_start, ac_action_y_start, ac_action_end, ac_action_y_end, color=bg_color_graphic, text=[msg], grow='left')
                        frame, ac_team_topleft, ac_team_bottomright = generate_diamond(ac_team_center_x, ac_team_center_y, ac_team_length, color=bg_color_black)
                        player_topleft, player_bottomright, _ = generate_rect(ac_name_start, ac_name_y_start, ac_name_end, ac_name_y_end, color=bg_color_black, text=[player_name], grow='left', font_scale=0.5)

                        frame = generate_center_logo(home_logo_url, in_team1_width, in_team1_height, ac_team_center_x, ac_team_center_y, ac_team_center_x, ac_team_center_y)

                        generate_center_text(player_name, player_topleft[0]/width, ac_name_y_start, player_bottomright[0]/width, ac_name_y_end, color=text_color_white, font_scale=0.7, thickness=2)
                        generate_center_text(msg, action_topleft[0]/width, ac_action_y_start, action_bottomright[0]/width, ac_action_y_end, color=text_color_graphic, font_scale=0.5, thickness=2, position=0.1)
            # Write the frame
            out.write(frame)
        
        # Release video-writer
        out.release()
        return output_filename
    