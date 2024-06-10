import json
import os
import re
import requests
import subprocess
import time
import m3u8
import io
import glob
from typing import Dict, List
from utils import run_and_log
from graphics import GraphicsTemplate
from session_manager import session

current_path_config = None
AUDIO_BITRATE_DEFAULT = '128k'
CRF_HIGH_QUALITY = 18
CRF_OUTPUT_VIDEO = 22

class Clip:
    def __init__(self, config: Dict, local_file_name: str, graphic_data):
        self.local_file_name = local_file_name
        self.local_file_name_duration = None
        self._info_cache = None
        self.config = config
        self.encoding_params = config.get('encoding_params', {})
        self.aspect_ratio = self.encoding_params.get('aspect_ratio', None)
        self.platform = self.encoding_params.get('platform', None)
        self.bitrate = self.encoding_params.get('video_bitrate', None)
        self.audio_bitrate = self.encoding_params.get('audio_bitrate', None)
        self.audio_tracks = self.encoding_params.get('audio_tracks', None)
        self.destination = config.get('destination', {}).get('path', {None})
        self.num_audio_streams = 1
        self.graphic = self.initialize_graphics(graphic_data)

    def initialize_graphics(self, graphic_data):
        try:
            json_file_path = path_graphic('main_template.json')
            with open(json_file_path, 'r') as file:
                data = json.load(file)
                template = data['general_settings']['template']
                
                if not template:
                    print(f"'No template for found, graphics are disabled.")
                    return None
                
                graphics = GraphicsTemplate()
                
                if not graphics.initialize(self, graphic_data):
                    print(f'Could not initialize graphic template {template}')
                    return None
                        
                return graphics
        except Exception as e:
            print(f"Error loading graphic_template: {e}")
            return None
        
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
    
    def file_duration(self):
        if self.local_file_name is not None and os.path.isfile(self.local_file_name):
            if self.local_file_name_duration is None:
                self.local_file_name_duration = float(subprocess.check_output(
                    ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                     '-of', 'default=noprint_wrappers=1:nokey=1', self.local_file_name]))
            return self.local_file_name_duration
        raise Exception('File does not exist: %s' % self.local_file_name)
    
    def duration(self):
        return self.end_offset_s - self.start_offset_s

    def path(self):
        return self.destination
    
def get_response(url: str, timeout: int = 2, retries: int = 2) -> requests.Response:
    headers = {'X-Forzify-Client': 'telenor-internal'}# if IN_CLOUD else {}
    for attempt in range(retries):
        try:
            response = session.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            if attempt >= retries - 1:
                #log.error(f'Error fetching {url} after {retries} attempts: {e}')
                print(f'Error fetching {url} after {retries} attempts: {e}')
                raise
            time.sleep(0.2)

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
def modify_graphic(setting, value):
    json_file_path = path_graphic('main_template.json')

    with open(json_file_path, 'r') as file:
        data = json.load(file)
    
    if setting == 'home_color' or setting == 'visiting_color':
        for i in range(len(value)):
            data["general_settings"][setting][i]= value[i]

    data["general_settings"][setting] = value
    
    with open(json_file_path, 'w') as file:
        json.dump(data, file, indent=4)


def modify_config(config_file, type, value, index=0):
    clip_meta = ["home_logo_url", "home_name", "home_initials", "visiting_logo_url", "visiting_name", "visiting_initials", "league_logo_url", "league_name", "league_name", "action"]
    json_file_path = path_config(config_file)

    with open(json_file_path, 'r') as file:
        data = json.load(file)

    if(type == 'graphic_template'):
        data['clip_parameters']['clip_graphic_template'][type] = value
    elif(type in clip_meta):
        data['clips'][index]['clip_meta'][0][type] = value
    elif(type == 'platform' or type == 'aspect_ratio'):
        data['encoding_parameters'][type] = value
    

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
    real_use = True
    while True:
        print("Choose a config template (default: example_1clip.json): \n1. example_1clip.json\n2. example_2clip.json")
        choice = input("Enter your choice (1/2): ")

        if choice == '1':
            config = 'example_1clip.json'
            current_path_config = path_config(config)
            
        elif choice == '2':
            config = 'example_2clip.json'
            current_path_config = path_config(config)
            
        else:
            print(f"Error resolving input '{choice}'")
            continue
        break

    while real_use:
        ptemp = 'platform'
        atemp = 'aspect_ratio'
        print("Choose a platform for encoding (default: youtube): \n1. Youtube (16:9)\n2. Tiktok (9:16)\n3. Instagram (1:1)\n4. Facebook (1:1)")
        choice = input("Enter your choice (1/2/3/4): ")

        if choice == '1' or choice == 'youtube':
            modify_config(config, ptemp, 'youtube')
            modify_config(config, atemp, [16, 9])
        elif choice == '2' or choice == 'tiktok':
            modify_config(config, ptemp, 'tiktok')
            modify_config(config, atemp, [9, 16])
        elif choice == '3' or choice == 'instagram':
            modify_config(config, ptemp, 'instagram')
            modify_config(config, atemp, [1, 1])
        elif choice == '4' or choice == 'facebook':
            modify_config(config, ptemp, 'facebook')
            modify_config(config, atemp, [1, 1])
        else:
            print(f"Error resolving input '{choice}'")
            continue
        break

    while real_use:
        orientation = ''
        setting = "graphic_layout"
        print("Choose the layout (default: left): \n1. Left\n2. Center")
        choice = input("Enter your choice (1/2): ")

        if choice == '1' or choice == 'left':
            orientation = 'left'
            modify_graphic(setting, orientation)
        elif choice == '2' or choice == 'center':
            orientation = 'center'
            modify_graphic(setting, orientation)
        else:
            print(f"Error resolving input '{choice}'")
            continue
        break

    while real_use:
        graphic_pack = ''
        setting = "template"
        print("Choose a graphic pack (default: Rectangle): \n1. Rectangle\n2. Diamond")
        choice = input("Enter your choice (1/2): ")

        if choice == '1' or choice == 'rectangle':
            graphic_pack = 'rectangle'
            modify_graphic(setting, graphic_pack)
        elif choice == '2' or choice == 'diamond':
            graphic_pack = 'diamond'
            modify_graphic(setting, graphic_pack)
        else:
            print(f"Error resolving input '{choice}'")
            continue
        break

    while real_use:
        print(f"Would you like to change the metadata and select a theme?")
        choice = input("Enter your choice (y/yes/n/no): ")

        if choice == 'yes' or choice == 'y':
            cmeta = 'action'
            # Iterates over all clips in config, repeats itself only when multiple clips are present in config.
            for i in range(count_clips(config)):
                while True:
                    print(f"Choose an action for clip {i+1} out of {count_clips(config)} (default: goal): \n1. Goal\n2. Shot\n3. Yellow card\n4. Red card\n5. Penalty")
                    choice = input("Enter your choice (1/2/3/4/5): ")
                    if choice == '1':
                        modify_config(config, cmeta, 'goal', i)
                    elif choice == '2':
                        modify_config(config, cmeta, 'shot', i)
                    elif choice == '3':
                        modify_config(config, cmeta, 'yellow card', i)
                    elif choice == '4':
                        modify_config(config, cmeta, 'red card', i)
                    elif choice == '5':
                        modify_config(config, cmeta, 'penalty', i) 
                    else:
                        print(f"Error resolving input '{choice}'")
                        continue
                    break
            
            # Select a league and the league's color theme
            while real_use:                
                setting = 'graphic_template'
                league_url = 'league_logo_url'
                league_n = 'league_name'
                print("Choose a league or a color-theme (default: J1 League): \n1. J1 League\n2. Eredivisie\n3. Allsvenskan\n4. Red\n5. Green\n6. En eller annen farge")
                choice = input("Enter your choice (1/2/3/4/5/6): ")
                if choice == '1':
                    modify_config(config, setting, 'j1_league')
                elif choice == '2':
                    modify_config(config, setting, 'eredivisie')
                elif choice == '3':
                    modify_config(config, setting, 'allsvenskan')
                elif choice == '4':
                    modify_config(config, setting, 'red')
                elif choice == '5':
                    modify_config(config, setting, 'green') 
                elif choice == '6':
                    modify_config(config, setting, 'purple')
                else:
                    print(f"Error resolving input '{choice}'")
                    continue
                
                # Choosing a league will result in all clips having the same theme. Therefor will all League logos be same for every clip.
                for i in range(count_clips(config)):
                    if choice == '1':
                        modify_config(config, league_url, "league/j1.png", i)
                        modify_config(config, league_n, "J1 League", i)
                    elif choice == '2':
                        modify_config(config, league_url, "league/eredivisie.png", i)
                        modify_config(config, league_n, "Eredivisie", i)
                    elif choice == '3':
                        modify_config(config, league_url, "league/allsvenskan.png", i)
                        modify_config(config, league_n, "Allsvenskan", i)
                break
            # Select home team and visiting team
            for i in range(count_clips(config)):
                while True:
                    home_n = "home_name" # Name of team
                    home_i = "home_initials" # Initials of team
                    home_c = "home_color" # Jersey color of team
                    home_url = "home_logo_url" # Url of team logo
                    print(f"Choose the HOME team for clip {i +1} out of {count_clips(config)} (default: FC Tokyo): \n1. FC Tokyo\n2. Kashima Antlers\n3. Urawa Red Diamond\n4. Tokyo Verdy\n5. PSV Eindhoven\n6. Fortuna Sittard\n7. FC Volendam\n8. Sparta Rotterdam")
                    choice = input("Enter your choice (1/2/3/4/5/6): ")
                    if choice == '1':
                        modify_config(config, home_n, 'FC Tokyo', i) # Changes name of home team 
                        modify_config(config, home_i, 'FCT', i) # Changes the initials for the home team
                        modify_graphic(home_c, ["#002B67","#FF0B33"]) # Changes the team's colors according to jersey
                        modify_config(config, home_url, "team/tokyo.png", i) # Changes local url to team's logo
                    elif choice == '2':
                        modify_config(config, home_n, 'Kashima Antlers', i)
                        modify_config(config, home_i, 'KASM', i)
                        modify_graphic(home_c, ["#ffffff","#ffffff"])
                        modify_config(config, home_url, "team/kashima.png", i)
                    elif choice == '3':
                        modify_config(config, home_n, 'Urawa Red Diamond', i)
                        modify_config(config, home_i, 'URAW', i)
                        modify_graphic(home_c, ["#ffffff","#CFCED2"])
                        modify_config(config, home_url, "team/urawa.png", i)
                    elif choice == '4':
                        modify_config(config, home_n, 'Tokyo Verdy', i)
                        modify_config(config, home_i, 'TK-V', i)
                        modify_graphic(home_c, ["#ffffff","#ffffff"])
                        modify_config(config, home_url, "team/tokyoverdy.png", i)
                    elif choice == '5':
                        modify_config(config, home_n, 'PSV Eindhoven', i) 
                        modify_config(config, home_i, 'PSV', i)
                        modify_graphic(home_c, ["#ffffff","#ED1C24"])
                        modify_config(config, home_url, "team/psv.png", i)
                    elif choice == '6':
                        modify_config(config, home_n, 'Fortuna Sittard', i)
                        modify_config(config, home_i, 'FOR', i)
                        modify_graphic(home_c, ["#000000","#000000"])
                        modify_config(config, home_url, "team/fortuna.png", i)
                    elif choice == '7':
                        modify_config(config, home_n, 'FC Volendam', i)
                        modify_config(config, home_i, 'VOL', i)
                        modify_graphic(home_c, ["#ee7f00","#ffffff"])
                        modify_config(config, home_url, "team/volendam.png", i)
                    elif choice == '8':
                        modify_config(config, home_n, 'Sparta Rotterdam', i)
                        modify_config(config, home_i, 'SPA', i)
                        modify_graphic(home_c, ["#466173","#466173"])
                        modify_config(config, home_url, "team/rotterdam.png", i)
                    else:
                        print(f"Error resolving input '{choice}'")
                        continue
    
                    visiting_n = "visiting_name"
                    visiting_i = "visiting_initials"
                    visiting_c = "visiting_color"
                    visiting_url = "visiting_logo_url"
                    print(f"Choose the VISITING team for clip {i +1} out of {count_clips(config)} (default: FC Tokyo): \n1. FC Tokyo\n2. Kashima Antlers\n3. Urawa Red Diamond\n4. Tokyo Verdy\n5. PSV Eindhoven\n6. Fortuna Sittard\n7. FC Volendam\n8. Sparta Rotterdam")
                    choice = input("Enter your choice (1/2/3/4/5/6): ")
                    if choice == '1':
                        modify_config(config, visiting_n, 'FC Tokyo', i)
                        modify_config(config, visiting_i, 'FCT', i)
                        modify_graphic(visiting_c, ["#002B67","#FF0B33"])
                        modify_config(config, visiting_url, "team/tokyo.png", i) # Changes local url to team's logo
                    elif choice == '2':
                        modify_config(config, visiting_n, 'Kashima Antlers', i)
                        modify_config(config, visiting_i, 'KASM', i)
                        modify_graphic(visiting_c, ["#ffffff","#ffffff"])
                        modify_config(config, visiting_url, "team/kashima.png", i)
                    elif choice == '3':
                        modify_config(config, visiting_n, 'Urawa Red Diamond', i)
                        modify_config(config, visiting_i, 'URAW', i)
                        modify_graphic(visiting_c, ["#ffffff","#CFCED2"])
                        modify_config(config, visiting_url, "team/urawa.png", i)
                    elif choice == '4':
                        modify_config(config, visiting_n, 'Tokyo Verdy', i)
                        modify_config(config, visiting_i, 'TK-V', i)
                        modify_graphic(visiting_c, ["#ffffff","#ffffff"])
                        modify_config(config, visiting_url, "team/tokyoverdy.png", i)
                    elif choice == '5':
                        modify_config(config, visiting_n, 'PSV Eindhoven', i) 
                        modify_config(config, visiting_i, 'PSV', i)
                        modify_graphic(visiting_c, ["#ffffff","#ED1C24"])
                        modify_config(config, visiting_url, "team/psv.png", i)
                    elif choice == '6':
                        modify_config(config, visiting_n, 'Fortuna Sittard', i)
                        modify_config(config, visiting_i, 'FOR', i)
                        modify_graphic(visiting_c, ["#000000","#000000"])
                        modify_config(config, visiting_url, "team/fortuna.png", i)
                    elif choice == '7':
                        modify_config(config, visiting_n, 'FC Volendam', i)
                        modify_config(config, visiting_i, 'VOL', i)
                        modify_graphic(visiting_c, ["#ee7f00","#ffffff"])
                        modify_config(config, visiting_url, "team/volendam.png", i)
                    elif choice == '8':
                        modify_config(config, visiting_n, 'Sparta Rotterdam', i)
                        modify_config(config, visiting_i, 'SPA', i)
                        modify_graphic(visiting_c, ["#466173","#466173"])
                        modify_config(config, visiting_url, "team/rotterdam.png", i)
                    else:
                        print(f"Error resolving input '{choice}'")
                        continue
                    break
        elif choice == 'no' or choice == 'n':
            break
        else:
            print(f"Error resolving input '{choice}'")
            continue
        break

def open_config():
    if current_path_config is None:
        print(f"{current_path_config} was not found. ")
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
            return graphic_data.get(graphic_template), graphic_data.get("general_settings")
    except Exception as e:
        # log.error(f'An error occured while loading graphic: {e}')
        return None

def initialize_clip(clip_config, clip_params, encoding_params, config, i, graphic_data):
    clip_config['graphic_template'] = clip_params.get('clip_graphic_template', {}).get('graphic_template', None)
    clip_config['name'] = config['name']
    clip_config['encoding_params'] = encoding_params
    return Clip(clip_config, config['clips'][i].get('video_url', None), graphic_data)

def process_clips(config, clip_params, encoding_params):
    total_clips = len(config['clips'])
    is_compilation = total_clips > 1
    video_h = None
    video_w = None
    fps = None
    platform = None
    clips = []
    
    graphic_template = clip_params.get('clip_graphic_template', {}).get('graphic_template', None)
    
    graphic_data, graphic_settings = get_graphic(graphic_template, config)
    
    for i, clip_config in enumerate(config['clips']):
        tpc = time.perf_counter()
       
        clip = initialize_clip(clip_config, clip_params, encoding_params, config, i, graphic_data)
        
        if clip.graphic:
            clip.graphic.download_and_meta(video_h, video_w, fps, is_compilation, platform, graphic_settings, i)
        
        clips.append(clip)
        print(f'Added video with meta graphic {i + 1}/{total_clips} with duration {clip.file_duration():.2f} seconds in {time.perf_counter()-tpc:.2f}')
    
    return video_h, video_w, fps, platform, clips, is_compilation

def merge_all_videos(clips: List[Clip], mp4_file: str, clip_params: dict, video_bitrate: str = None, audio_bitrate: str = None):
    if not clips:
        print('No clips were found to process')
        return
    
    ffmpeg_cmd = ''
    
    for i, _ in enumerate(clips):
        ffmpeg_cmd += f'-i video/{i}_meta.mp4 '

    ffmpeg_cmd += "-filter_complex "

    concat_cmd = ""
    for i, _ in enumerate(clips):
        concat_cmd += f"[{i}:v]"
    concat_cmd += f"concat=n={len(clips)}:v=1:a=0[v]"
        
    ffmpeg_cmd += f'"{concat_cmd}" -map "[v]" video/output.mp4'

    return ffmpeg_cmd

def process_encode_final(clips, clip_params, is_comp, encoding_params):
    mp4_filename = f'video/output.mp4'
   
    if os.path.exists(mp4_filename):
        os.remove(mp4_filename)
        print(f"Existing {mp4_filename} deleted successfully.")

    if is_comp:
        ffmpeg_cmd = merge_all_videos(clips, mp4_filename, clip_params, encoding_params.get('video_bitrate'), encoding_params.get('audio_bitrate'))
        tpc = time.perf_counter()
        run_and_log(f'ffmpeg -hide_banner -progress progress-log.txt -loglevel warning -y {ffmpeg_cmd}', shell=True)
        
        #log.info(f'Final video encoded in {time.perf_counter() - tpc:.2f} seconds.)
    else:
        single_clip_filename = 'video/0_meta.mp4'
        os.rename(single_clip_filename, mp4_filename)
        #log.info(f'Single clip moved to {mp4_filename}')

    return mp4_filename

def verify_file(filename):
    return filename and os.path.exists(filename) and os.path.getsize(filename) > 0

def clean_up():
    file_pattern = 'video/*_meta.mp4'
    files_to_remove = glob.glob(file_pattern)

    for file_path in files_to_remove:
        try:
            os.remove(file_path)
            print(f"Successfully deleted file: {file_path}")
        except Exception as e:
            print(f"Failed to delete file {file_path}: {e}")

def main():
    global_start_time = time.perf_counter()
    mp4_filename = None
    success = False
    
    #try:
    user_options()
    config = open_config()
    encoding_params = config.get('encoding_parameters', {})
    clip_params = config.get('clip_parameters', {})
    
    #log_initial_params(config, encoding_params, clip_params)
    video_h, video_w, fps, platform, clips, is_comp = process_clips(config, clip_params, encoding_params)

    mp4_filename = process_encode_final(clips, clip_params, is_comp, encoding_params)
    print(mp4_filename)
    if verify_file(mp4_filename):
        success = True
    else:
        print('Failed to create valid mp4 file.')
            
    #except Exception as e:
        #print(f'An error has occured: {e}')
    #finally:
    global_end_time = time.perf_counter()
    #log.info(f'[reels] Total time taken for entire process: {global_end_time - global_start_time:.2f} seconds.')
    print(f'[reels] Total time taken for entire process: {global_end_time - global_start_time:.2f} seconds.')

    if success:
        print('Successfully completed entire process')
    else:
        print('Failed to compelete entire process')

    clean_up()

if __name__ == '__main__':
    main()

