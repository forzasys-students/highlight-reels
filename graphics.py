import requests
import os
import cv2
import time
import logging
from PIL import Image, ImageDraw, ImageFont
from urllib.parse import urlparse

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
        
    def download_and_meta(self, video_w, video_h, fps, is_compilation, platform):
        #tpc = time.perf_counter()

        audio_codec_part, video_codec_part = self.clip.download(is_compilation)

        video_h = self.clip.video_height()
        video_w = self.clip.video_width()
        fps = self.clip.frame_rate()

        
        generate_meta = False
        for meta in self.clip.config['clip_meta']:
            action = meta['action']
            if action in included_events:
                generate_meta = True

        if not generate_meta:
            return
        
        output_file = create_animated_meta(video_h, video_w, self.clip.config['clip_meta'], self.fg_color, self.bg_color, self.border_color, self.text_color, self.clip.local_file_name, self.clip.aspect_ratio)

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

def create_animated_meta(video_h, video_w, clip_meta, fg_color, bg_color, border_color, text_color, local_file_name, aspect_ratio=[16, 9], fps=25.0):
    for i, meta in enumerate(clip_meta):
        home_logo_url = meta['homo_logo_url']
        visiting_logo_url = meta['visiting_logo_url']
        league_logo_url = meta['league_logo_url']

        icon, msg = get_action_message_and_icon(meta, language='EN')

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
        
        # Initialize dimensions for logos
        logo_box_dim = round(logo_box_dim_ratio * video_h * 0.66)
        logo_dim = round(logo_dim_ratio * video_h * 0.3)
        league_logo_dim = round(league_logo_dim_ratio * video_h * 0.66)
        
        # Initialize font-size and font-type
        font_path = os.path.join('resources', 'font', 'Montserrat-VariableFont_wght')
        msg_font = ImageFont.truetype('font_path', msg_font_size)

        # Download logos
        home_logo = get_img(home_logo_url)
        home_logo.thumbnail((logo_dim, logo_dim))
        visiting_logo = get_img(visiting_logo_url)
        visiting_logo.thumnail((logo_dim, logo_dim))
        league_logo = get_img(league_logo_url)
        league_logo.thumbail((league_logo_dim, league_logo_dim))

        # Initialize video capture 
        cap = cv2.VideoCapture(local_file_name)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))

        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        output_filename = local_file_name.replace('.mp4', '_meta.mp4')
        out = cv2.VideoWriter(output_filename, fourcc, fps, (width, height))

        duration = 8 * fps
        min_x
    
    

def get_action_message_and_icon(meta, language='EN'):
    team_logo_url = meta['team_logo_url']
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
        