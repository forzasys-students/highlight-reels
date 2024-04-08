import json
import os
import re
import requests
import subprocess

from graphics import GraphicsTemplate

current_path_config = None

class Clip:
    def __init__(self, config: Dict, local_file_name: str, graphic_data):
        self.local_file_name = local_file_name
        self.local_file_name_duration = None
        self._info_cache = None
        self.config = config
        self.encoding_params = config.get('encoding_params', {})
        self.aspect_ratio = self.encoding_params.get('aspect_ratio', None)
        self.cropping = self.encoding_params.get('cropping',None)
        self.bitrate = self.encoding_params.get('video_bitrate', None)
        self.audio_bitrate = self.encoding_params.get('audio_bitrate', None)
        self.audio_tracks = self.encoding_params.get('audio_tracks', None)
        self.num_audio_streams = 1
        self.graphic = self.initialize_graphics(graphic_data)

        # Intro
        # if self.aspect_ratio:
        #     self.aspect_ratio = [int(x) for x in self.aspect_ratio.split(':')]
        #     if self.aspect_ratio == [9, 16]:
        #         self.sef_default_path = "./sef/cropped9_16/"
        #     elif self.aspect_ratio == [1, 1]:
        #         self.sef_default_path = "./sef/cropped1_1/"
        #     elif self.aspect_ratio == [4, 5]:
        #         self.sef_default_path = "./sef/cropped4_5/"
        #     else:
        #         log.exception("Only supported aspect ratios for SEF game highlight are 16:19 , 9:16, 4:5 and 1:1!")
        # else:
        #     self.sef_default_path = "./sef/"

        # Transition
        # if self.config['transition_type'] == 4:
        #     self.start_offset_s = 0
        #     self.end_offset_s = 3
        #     self.ai_producer_start_offset_s = None
        #     self.ai_producer_end_offset_s = None
        #     self.video_url = None
        #     return

    def initialize_graphics(self, graphic_data):
        if graphic_data is None:
            #log.info('An error occured when loading graphic_data. Graphics will be disabled.')
            return None
        
        template_name = graphic_data.get('template', {}).get('name', None)
        graphics = None

        if template_name == 'ForzaSys':
            graphics = FSGraphicsTemplate()
            #log.info('Template ForzaSys applied')
        else:
            #log.warning(f'No template for {template_name} was found. Graphics will be disabled.')
            return None
        
        if not graphics.initialize(self, graphic_data):
            #log.error(f'Could not initialize graphic template {template_name}.')
            return None
        
        return graphics
    
    def _fetch_video_info(self):
        if self._info_cache is not None:
            return self._info_cache
        
        if self.local_file_name is not None and os.path.isfile(self.local_file_name):
            probe = subprocess.check_output(
                ['ffprobe',
                 '-v', 'error',
                 '-show_entries', 'format=duration:stream=avg_frame_rate:stream=height:stream=width',
                 '-of', 'json',
                 self.local_file_name]
            )
            self._info_cache = json.loads(probe)
            return self._info_cache
        else:
            raise Exception(f'File not found: {self.local_file_name}')

    def frame_rate(self):
        info = self._fetch_video_info()
        fps_str = info["streams"][0]["avg_frame_rate"]

        if '/' in fps_str:
            num, den = fps_str.split('/')
            fps = float(num) / float(den)
        else:
            fps = float(fps_str)

        return fps
    
    def video_height(self):
        info = self._fetch_video_info()
        return info['streams'][0]['height']
            
    def video_width(self):
        info = self._fetch_video_info()
        return info["streams"][0]["width"]


# Utilizes a web-api to GET data regarding hexadecimal value, i.e. name of the color
def translate_color(hex_color, target_language='en'):
    url = f"https://www.thecolorapi.com/id?hex={hex_color.lstrip('#')}"
    response = requests.get(url)
    data = response.json()

    if 'name' in data:
        color_name = data['name']['value']
        return color_name
    else:
        return 'Unknown color'

# Checks and ensures that inputted hexadecimal value is "legal" and matches pattern
def is_valid_hex(color):
    pattern = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'

    if re.match(pattern, color):
        trans_color = translate_color(color)
        if trans_color != 'Unknown color':
            print(f"Color '{trans_color}' was applied.")
            return True
        else:
            print(trans_color)
    else:
        return False

# Requests user-input of different hex. values and applies if inputted properly
def user_custom():
    while True:
        print("Choose the foreground color (hex code) ")
        choice = input("Enter a hexadecimal color: ")

        if is_valid_hex(choice):
            modify_graphic('fg_color', choice)
            break
        else:
            print("Invalid hexadecimal format")

    while True:
        print("Choose the background color (hex code) ")
        choice = input("Enter a hexadecimal color: ")

        if is_valid_hex(choice):
            modify_graphic('bg_color', choice)
            break
        else:
            print("Invalid hexadecimal format")

    while True:
        print("Choose the border color (hex code) ")
        choice = input("Enter a hexadecimal color: ")

        if is_valid_hex(choice):
            modify_graphic('border_color', choice)
            break
        else:
            print("Invalid hexadecimal format")

    while True:
        print("Choose the text color (hex code)\nRecommend white (#FFFFFF) or black (#000000) ")
        choice = input("Enter a hexadecimal color: ")

        if is_valid_hex(choice):
            modify_graphic('text_color', choice)
            break
        else:
            print("Invalid hexadecimal format")

# Current method used for pathing files on Windows
def path_config(config_file):
    current_dir = os.path.dirname(os.path.abspath(__file__))

    folder_name='config_template'

    folder_path = os.path.join(current_dir, folder_name)

    file_name=config_file

    json_file_path = os.path.join(folder_path, file_name)

    return json_file_path

def path_graphic(graphic_file):
    current_dir = os.path.dirname(os.path.abspath(__file__))

    folder_name ='graphic_templates'

    folder_path = os.path.join(current_dir, folder_name)

    file_name = graphic_file

    json_file_path = os.path.join(folder_path, file_name)

    return json_file_path

# Edit color config of main_template.json
def modify_graphic(color_config, hex_color):
    
    json_file_path = path_graphic('main_template.json')

    with open(json_file_path, 'r') as file:
        data = json.load(file)

    data["custom_template"][color_config] = hex_color
    
    with open(json_file_path, 'w') as file:
        json.dump(data, file, indent=4)


def modify_config(config_file, type, value, index=0):
    json_file_path = path_config(config_file)

    with open(json_file_path, 'r') as file:
        data = json.load(file)

    if(type == 'graphic_template'):
        data['clip_parameters']['clip_graphic_template'][type] = value
    elif(type == 'action'):
        data['clips'][index]['clip_meta'][0][type] = value

    with open(json_file_path, 'w') as file:
        json.dump(data, file, indent=4)

# Returns x-count clips from specified config_template
def count_clips(config_json):
    json_path_file = path_config(config_json)

    with open(json_path_file, 'r') as file:
        data = json.load(file)

    if 'clips' in data:
        return len(data['clips'])
    else:
        return 0

# Configurates config_template & graphic_template according to user-input
def user_options():
    global current_path_config
    config = None
    while True:
        cmeta = 'action'
        print("Choose a config template (default: example_1clip.json): \n1. example_1clip.json\n2. example_8clip.json")
        choice = input("Enter your choice (1/2): ")

        if choice == '1':
            config = 'example_1clip.json'
            current_path_config = path_config(config)
            while True:
                print("Choose an action for the clip (default: goal): \n1. Goal\n2. Shot\n3. Yellow card\n4. Red card\n5. Penalty")
                choice = input("Enter your choice (1/2/3/4/5): ")
                if choice == '1':
                    modify_config(config, cmeta, 'goal')
                elif choice == '2':
                    modify_config(config, cmeta, 'shot')
                elif choice == '3':
                    modify_config(config, cmeta, 'yellow card')
                elif choice == '4':
                    modify_config(config, cmeta, 'red card')
                elif choice == '5':
                    modify_config(config, cmeta, 'penalty')
                else:
                    print(f"Error resolving input '{choice}'")
                    continue
                break
            break
        elif choice == '2':
            config = 'example_8clip.json'
            current_path_config = path_config(config)
            num_clip = 0
            while num_clip < count_clips(config):
                while True:
                    print(f"Choose an action for clip #{num_clip+1} (default: goal): \n1. Goal\n2. Shot\n3. Yellow card\n4. Red card\n5. Penalty")
                    choice = input("Enter your choice (1/2/3/4/5): ")
                    if choice == '1':
                        modify_config(config, cmeta, 'goal', num_clip)
                    elif choice == '2':
                        modify_config(config, cmeta, 'shot', num_clip)
                    elif choice == '3':
                        modify_config(config, cmeta, 'yellow card', num_clip)
                    elif choice == '4':
                        modify_config(config, cmeta, 'red card', num_clip)
                    elif choice == '5':
                        modify_config(config, cmeta, 'penalty', num_clip) 
                    else:
                        print(f"Error resolving input '{choice}'")
                        continue
                    num_clip += 1
                    break
            break
        else:
            print(f"Error resolving input '{choice}'")

    while True:
        gtemp = 'graphic_template'
        print("Choose a color template (default: yellow): \n1. Red\n2. Orange\n3. Yellow\n4. Custom")
        choice = input("Enter your choice (1/2/3/4): ")

        if choice == '1' or choice == 'red':
            modify_config(config, gtemp, 'red_template')
            break
        elif choice == '2' or choice == 'orange':
            modify_config(config, gtemp, 'orange_template')
            break
        elif choice == '3' or choice == 'yellow':
            modify_config(config, gtemp, 'yellow_template')
            break
        elif choice == '4' or choice == 'custom':
            user_custom()
            modify_config(config, gtemp, 'custom_template')
            break
        else:
            print(f"Error resolving input '{choice}' ")

def log_initial_params(config, encoding_params, clip_params):
    # log.info(
    #     f'Parameters are as below:\n'
    #     f'Encoding Params: {encoding_params}\n'
    #     f'Clip Params: {clip_params}\n'
    #     f'Clips: \n {config["clips"]}'
    # )
    pass

def report_exit(msg, success=False):
    # if success:
    #     log.info(msg)
    # else:
    #     log.error(msg)
    
    exit(0 if success else 1)

def open_config():
    if current_path_config is None:
        report_exit("Config not found or specified")

    try:
        with open(current_path_config, 'r') as f:
            return json.loads(f.read())
    except Exception as e:
        # log.error(f'An error occured while opening config: {e}')
        return None
    
def get_graphic(graphic_template, config):
    if graphic_template is None:
        return None
    try:
        with open(path_graphic('main_template.json'), 'r') as f:
            graphic_data = json.load(f)
            return graphic_data.get('graphic_template')
    except Exception as e:
        # log.error(f'An error occured while loading graphic: {e}')
        return None

def initialize_clip(clip_config, clip_params, encoding_params, config, i, graphic_data):
    clip_config['graphic_template'] = clip_params.get('clip_graphic_template', {}).get('graphic_template', None)
    clip_config['enconding_params'] = encoding_params
    return Clip(clip_config, f'video/{i}.mp4', graphic_data)

def process_clips(config, clip_params, encoding_params):
    total_clips = len([config['clips']])
    is_compilation = total_clips > 1
    video_h = None
    video_w = None
    fps = None
    clips = []

    graphic_template = clip_params.get('clip_graphic_template', {}).get('graphic_template', None)
    graphic_data = get_graphic(graphic_template, config)

    for i, clip_config in enumerate(config['clips']):
        # tpc = time.perf_counter()

        clip = initialize_clip(clip_config, clip_params, encoding_params, config, i, graphic_data)
        if clip.graphic:
            #if clip intro and outro
                #is_compilation = true
            clip.graphic.download_and_meta

def main():
    try:
        user_options()
        config = open_config()

        encoding_params = config.get('encoding_parameters', {})
        clip_params = config.get('clip_parameters', {})

        log_initial_params(config, encoding_params, clip_params)

        video_h, video_w, fps, clips, is_comp = process_clips(config, encoding_params, clip_params)
    except Exception as e:
        # log.error(f'An error has occured: {e}')
        pass
    finally:


if __name__ == '__main__':
    main()

