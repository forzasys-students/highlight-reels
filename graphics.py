import requests
import os
import cv2
import time
import logging
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from urllib.parse import urlparse
from utils import run_and_log

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

        generate_meta = False
        for meta in self.clip.config['clip_meta']:
            action = meta['action']
            if action in included_events:
                generate_meta = True

        if not generate_meta:
            return
        
        create_animated_meta(video_h, video_w, self.clip.config['clip_meta'], self.bg_color, self.text_color, home_color, visiting_color, self.clip.local_file_name, clip_num, self.clip.aspect_ratio)
        
        print(f'Adding graphic overlay took: {time.perf_counter() - tpc}')
        
        

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
    folder_path = 'images'
    image_path = os.path.join(folder_path, image_name)

    with Image.open(image_path) as img:
        out = img.copy()
    
    return out

def create_animated_meta(video_h, video_w, clip_meta, bg_color, text_color, home_color, visiting_color, local_file_name, clip_num, aspect_ratio=[16, 9], fps=25.0):
    for i, meta in enumerate(clip_meta):
        home_logo_url = meta['home_logo_url']
        visiting_logo_url = meta['visiting_logo_url']
        league_logo_url = meta['league_logo_url']

        # Dynamic sizes
        if aspect_ratio == [16, 9] or aspect_ratio is None:
            aspect_ratio = [16, 9]
            logo_box_dim_ratio = 0.35
            logo_dim_ratio = 0.2
            msg_font_size = 25
            icon_dim_ratio = 0.15
            overlay_postion_y_offset = 0.92
            overlay_postion_x_offset = 0.05
        elif aspect_ratio == [9, 16]:
            logo_box_dim_ratio = 0.15
            logo_dim_ratio = 0.14
            msg_font_size = 18
            icon_dim_ratio = 0.1
            overlay_postion_y_offset = 0.92
            overlay_postion_x_offset = 0.1
        elif aspect_ratio == [1, 1]:
            logo_box_dim_ratio = 0.22
            logo_dim_ratio = 0.16
            msg_font_size = 23
            icon_dim_ratio = 0.11
            overlay_postion_y_offset = 0.92
            overlay_postion_x_offset = 0.1
        elif aspect_ratio == [4, 5]:
            logo_box_dim_ratio = 0.22
            league_logo_dim_ratio = 0.16
            msg_font_size = 23
            icon_dim_ratio = 0.11
            overlay_postion_y_offset = 0.92
            overlay_postion_x_offset = 0.1
        else:
            raise ValueError(f'Invalid aspect ratio entered: {aspect_ratio}.')
        
        
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
        
        
        i = 1
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            i += 1

            
            # Fade-in effect team logo
            if i < int(duration * 0.1):
                cv2.rectangle(frame, (100, 100), (200,200), (255,255,255), -1)
                if (clip_num == 1):
                    cv2.rectangle(frame, (100, 100), (200,200), (0,0,0), -1)
            # Convert PIL image back to cv2 image (numpy array)


            # Write the frame
            out.write(frame)
        
        # Release video-writer
        out.release()
        return output_filename
    

def get_action_message_and_icon(meta, language='EN'): 
    team_logo_url = meta['home_logo_url']
    score = meta['score']
    player_name = meta['player_name']
    
    icon, message = ''

    if language == 'EN':
        if meta['action'] == 'shot':
            icon = get_img_local('shot_icon.png')
            msg = 'Shot at goal'
        elif meta['action'] == 'goal':
            icon = get_img(team_logo_url)
            msg = 'Goal'
        elif meta['action'] == 'yellow card':
            icon = get_img_local('yellow_icon.png')
            msg = 'Yellow card'
        elif meta['action'] == 'red card':
            icon = get_img_local('red_icon.png')
            msg = 'Red card'
        elif meta['action'] == 'penalty':
            icon = get_img(team_logo_url)
        else:
            icon = get_img_local('ball_icon.png')
            msg = 'Missing action'

        if player_name:
            msg = f'{player_name}: {msg}'

        return icon, msg
        