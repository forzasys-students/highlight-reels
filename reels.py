import json
import os
import re
import requests
import subprocess
import time
import m3u8
import io
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
        self.platform = self.encoding_params.get('platform',None)
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

        if 'aiproducer' not in config or config['aiproducer']['video_url'] is None:
            # Without AIProducer
            re_match = re.match('.*/playlist.m3u8/(\d+):(\d+):(\d+)/Manifest.m3u8', config['video_url'])
            if re_match is None:
                print('Video url does not match given pattern: %s' % config['video_url'])

            start_offset_s = int(re_match[2])
            end_offset_s = int(re_match[3])
            if start_offset_s >= end_offset_s or end_offset_s - start_offset_s > 1000000:
                print('Weird end_ts or start_ts or super long playlist: %s' % config['video_url'])

            self.start_offset_s = start_offset_s / 1000.0
            self.end_offset_s = end_offset_s / 1000.0
            self.ai_producer_start_offset_s = None
            self.ai_producer_end_offset_s = None
            self.video_url = config['video_url']

    def initialize_graphics(self, graphic_data):
        if graphic_data is None:
            #log.info('An error occured when loading graphic_data. Graphics will be disabled.')
            return None
        
        template_name = graphic_data.get('template', {}).get('name', None)
        graphics = None

        if template_name == 'ForzaSys':
            graphics = GraphicsTemplate()
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
    
    def duration(self):
        return self.end_offset_s - self.start_offset_s

    def download(self, is_comp=True):
        padding = 0
        if self.video_url is None:
            #log.info('No video url specified for this clip and the graphic is disabled so skipping')
            print('No video url specified for this clip and the graphic is disabled so skipping')
            return
        
        tpc = time.perf_counter()
        print(self.video_url)
        local_video_path = self.local_file_name.replace('.mp4', '.ts')
        self.num_audio_streams = download_ts_files(self.video_url, local_video_path, self.audio_tracks)
        tpc1 = time.perf_counter()
        filter_crop = ""

        #if self.aspect_ratio:
        #   if self.cropping == 'smart':

        # Initialize ffmpeg command parts
        video_codec_part = '-c:v copy '
        audio_codec_part = '-c:a copy '
        audio_map = ''
        video_map = ''

        needs_video_encoding = is_comp or self.aspect_ratio or self.bitrate
        needs_audio_encoding = self.audio_bitrate and not is_comp

        if needs_video_encoding:
            video_codec_part = '-c:v libx264 -preset veryfast '
            if not is_comp and self.bitrate:
                video_codec_part += f' -b:v {self.bitrate} '
            elif not is_comp:
                video_codec_part += f' -crf {CRF_OUTPUT_VIDEO} '
            else:
                video_codec_part += f' -crf {CRF_HIGH_QUALITY} '

        if needs_audio_encoding:
            audio_codec_part = f'-c:a aac -b:a {self.audio_bitrate} '      

        if self.start_offset_s % 2 == 1:
            ffmpeg_command = (
                'ffmpeg -y -hide_banner -progress progress-log.txt -loglevel warning '
                f'-i {self.local_file_name.replace(".mp4", ".ts")} '
                f'-t {self.duration()} '
                f'-ss {self.ai_producer_start_offset_s + 1 if self.ai_producer_start_offset_s else 1} '
                f'{filter_crop} '
                f'{video_codec_part} '
                f'{audio_codec_part} '
                f'{video_map} '
                f'{audio_map} '
                f'{self.local_file_name}'
            )
        else:
            ffmpeg_command = (
                'ffmpeg -y -hide_banner -progress progress-log.txt  -loglevel warning '
                f'-i {self.local_file_name.replace(".mp4", ".ts")} '
                f'-t {self.duration()} '
                f'-ss {self.ai_producer_start_offset_s if self.ai_producer_start_offset_s else 0} '
                f'{filter_crop} '
                f'{video_codec_part} '
                f'{audio_codec_part} '
                f'{video_map} '
                f'{audio_map} '
                f'{self.local_file_name}'
            )
        run_and_log(ffmpeg_command, shell=True)
        #log.info('Video download took %.2f seconds, encoding took %.2f seconds' %
                 #((tpc1 - tpc), (time.perf_counter() - tpc1)))
        print('Video download took %.2f seconds, encoding took %.2f seconds' %
              ((tpc1 - tpc), (time.perf_counter() - tpc1)))
        
        return audio_codec_part, video_codec_part

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


def download_segments(manifest, filename, retries=2, backoff_factor=0.5):
    '''Download video or audio segments.'''
    headers = {'X-Forzify-Client': 'telenor-internal'}# if IN_CLOUD else {}
    for line in manifest.splitlines():
        if line.startswith('#'):
            continue
        for attempt in range(retries):
            try:
                with session.get(line, headers=headers, stream=True) as req:
                    req.raise_for_status()
                    # Create a new in-memory buffer for this segment
                    with io.BytesIO() as segment_buffer:
                        for chunk in req.iter_content(chunk_size=8192):
                            segment_buffer.write(chunk)

                        # Append after successfully downloading the segment
                        with open(filename, 'ab') as f:
                            segment_buffer.seek(0)
                            f.write(segment_buffer.read())

                        break
            except Exception as e:
                #log.info(f'Attempt {attempt+1} for downloading the segment failed: {e}')
                print(f'Attempt {attempt+1} for downloading the segment failed: {e}')
                time.sleep(attempt * backoff_factor)
        else:
            #log.error(f'Failed to download {line} after {retries} attempts')
            print(f'Failed to download {line} after {retries} attempts')


def process_default_audio_tracks(manifest, local_filename):
    '''Search in the manifest and download all available tracks'''
    audio_files_count = 0
    command_append_audio = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'warning', '-i', local_filename]
    temp_video = local_filename.replace('.ts', '_temp.ts')

    for media in manifest.media:
        if media.type == 'AUDIO':
            audio_files_count += 1
            # Download the audio segments
            audio_file = local_filename.replace('.ts', f'_{media.name}.ts')
            #log.info(f'Downloading audio segments from {media.absolute_uri}')
            segment_manifest = get_response(media.absolute_uri).text
            download_segments(segment_manifest, audio_file)
            command_append_audio.extend(['-i', audio_file])

    if audio_files_count > 0:
        # -map 0:v -map 1:a -map 2:a -c:v copy -c:a aac
        command_append_audio.extend(['-map', '0:v'])
        for i in range(len(manifest.media)):
            command_append_audio.extend(['-map', f'{i + 1}:a'])

        command_append_audio.extend(['-c:v', 'copy', '-c:a', 'copy', temp_video])
        run_and_log(command_append_audio, msg='Merging audio streams')
        # Now move the temporary video file to the final filename
        os.rename(temp_video, local_filename)

    return audio_files_count


def process_specific_audio_track(video_url, local_filename, audio_track):
    '''Handle case with a specific audio track selected.'''
    temp_video = local_filename.replace('.ts', '_temp.ts')
    audio_url = video_url.replace('Manifest.m3u8', f'audio{audio_track}/Manifest.m3u8')
    # Download audio segments
    audio_filename = local_filename.replace('.ts', f'_audio{audio_track}')
    audio_manifest = get_response(audio_url).text
    download_segments(audio_manifest, audio_filename)

    # Combine video and audio using ffmpeg for SHL videos
    subprocess.run([
        'ffmpeg',
        '-y', '-hide_banner', '-loglevel', 'warning',
        '-i', local_filename,
        '-i', audio_filename,
        '-c', 'copy',
        temp_video
    ])
    # Now move the temporary video file to the final filename
    os.rename(temp_video, local_filename)


def download_ts_files(video_url: str, local_filename: str, audio_track=None):
    # Select the highest quality stream and download it
    try:
        master_manifest = m3u8.loads(get_response(video_url).text)
        master_manifest.base_uri = video_url.replace('/Manifest.m3u8', '')

        hq_manifest = max(master_manifest.playlists, key=lambda p: p.stream_info.bandwidth)

        # Get the manifest for the highest quality stream
        segment_manifest = get_response(hq_manifest.absolute_uri).text
    except Exception as e:
        #log.error(f'Could not download from {video_url}. Error: {e}')
        print(f'Could not download from {video_url}. Error: {e}')
        raise e

    if segment_manifest is None:
        #log.error(f'Segment manifest is empty for high-quality manifest URI: {hq_manifest.absolute_uri}')
        print(f'Segment manifest is empty for high-quality manifest URI: {hq_manifest.absolute_uri}')
        raise Exception(f'Segment manifest is empty for high-quality manifest URI: {hq_manifest.absolute_uri}')
    download_segments(segment_manifest, local_filename)

    num_audio_streams = 0
    if audio_track is None:
        num_audio_streams = process_default_audio_tracks(master_manifest, local_filename)
    else:
        process_specific_audio_track(video_url, local_filename, audio_track)
        num_audio_streams = 1

    return num_audio_streams


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
        ptemp = 'platform'
        atemp = 'aspect_ratio'
        print("Choose a platform for encoding (default: youtube): \n1. Youtube (16:9)\n2. Tiktok (9:16)\n3. Instagram (1:1)\n4. Facebook (1:1)")
        coice = input("Enter your choice (1/2/3/4): ")

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

    while True:
        gtemp = 'graphic_template'
        print("Choose a color template (default: yellow): \n1. Red\n2. Orange\n3. Yellow\n4. Custom")
        choice = input("Enter your choice (1/2/3/4): ")

        if choice == '1' or choice == 'red':
            modify_config(config, gtemp, 'red_template')
        elif choice == '2' or choice == 'orange':
            modify_config(config, gtemp, 'orange_template')
        elif choice == '3' or choice == 'yellow':
            modify_config(config, gtemp, 'yellow_template')
        elif choice == '4' or choice == 'custom':
            user_custom()
            modify_config(config, gtemp, 'custom_template')
        else:
            print(f"Error resolving input '{choice}' ")
            continue
        break
    return
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
            return graphic_data.get(graphic_template)
    except Exception as e:
        # log.error(f'An error occured while loading graphic: {e}')
        return None

def initialize_clip(clip_config, clip_params, encoding_params, config, i, graphic_data):
    clip_config['graphic_template'] = clip_params.get('clip_graphic_template', {}).get('graphic_template', None)
    clip_config['name'] = config['name']
    clip_config['encoding_params'] = encoding_params
    return Clip(clip_config, f'video/{i}.mp4', graphic_data)

def process_clips(config, clip_params, encoding_params):
    total_clips = len([config['clips']])
    is_compilation = total_clips > 1
    video_h = None
    video_w = None
    fps = None
    platform = None
    clips = []
    
    graphic_template = clip_params.get('clip_graphic_template', {}).get('graphic_template', None)
    
    graphic_data = get_graphic(graphic_template, config)
    
    for i, clip_config in enumerate(config['clips']):
        # tpc = time.perf_counter()
        
        clip = initialize_clip(clip_config, clip_params, encoding_params, config, i, graphic_data)
        if clip.graphic:
            #if clip intro and outro
                #is_compilation = true
            clip.graphic.download_and_meta(video_h, video_w, fps, is_compilation, platform)
            #if i == 0 and clip.graphic.intro_screen:
                #add_intro(clip, clip_config, video_h, video_w, fps, platform, clips, graphic_data)
            clips.append(clip)
            #log.info(f'Added video with meta graphics {i + 1}/{total_clips} with duration {clip.file_duration():.2f} seconds in {time.perf_counter()-tpc:.2f}')

            #if i == (total_clips - 1) and clip.graphic.outro_screen:
                #is_compulation = True
                #add_outro(clip, clip_config, video_h, video_w, fps, platform, clips, graphic_data)
    
    return video_h, video_w, fps, platform, clips, is_compilation

def audio_copy(clip, max_audio_streams):
    new_streams = max_audio_streams - clip.num_audio_streams
    ffmpeg_cmd = 'ffmpeg -y -hide_banner -loglevel warning -i ' + clip.local_file_name

    if clip.num_audio_streams == 0:
        ffmpeg_cmd += ' -f lavfi -i anullsrc'
        new_streams -= 1

    for _ in range(new_streams):
        ffmpeg_cmd += ' -map 0:v -map 0:a -map 0:a'

    new_filename = clip.local_file_name.replace(".mp4", "_multiaudio.mp4")
    ffmpeg_cmd += ' -y -c copy -preset ultrafast ' + new_filename
    #log.info(f'Copy audio track: {ffmpeg_cmd}')
    run_and_log(ffmpeg_cmd, shell=True)

    if os.path.exists(clip.local_file_name):
        os.remove(clip.local_file_name)
    os.rename(new_filename, clip.local_file_name)
    clip.num_audio_streams = max_audio_streams

def merge_all_videos(clips: List[Clip], mp4_file: str, clip_params: dict, video_bitrate: str = None, audio_bitrate: str = None):
    if not clips:
        #log.error('No clips were found to process')
        return
    ffmpeg_cmd = ''

    max_audio_streams = max([clip.num_audio_streams for clip in clips], default=1)
    
    for i, clip in enumerate(clips):
        ffmpeg_cmd += f' -i {clip.local_file_name}'
        if clips[i].num_audio_streams != 0 and clips[i].num_audio_streams < max_audio_streams:
            audio_copy(clips[i], max_audio_streams)

    if clip_params.get('clip_transitions') and len(clips) > 1:
        ffmpeg_cmd += ' -filter_complex "\\\n'  # Start of filter complex
        # Audio track for the first two clips
        if max_audio_streams > 1:
            audio_chain = ''
            audio_map = ''
            for i in range(max_audio_streams):
                if len(clips) == 2:
                    audio_chain += f';\\\n[0:a:{i}][1:a:{i}]acrossfade=d={clips[1].config["transition_fade_duration"]}:c1=tri:c2=tri[a{i}]'
                    audio_map += f' -map "[a{i}]"'
                else:
                    audio_chain += f';\\\n[0:a:{i}][1:a:{i}]acrossfade=d={clips[1].config["transition_fade_duration"]}:c1=tri:c2=tri[a1-{i}]'            
        else:
            if len(clips) == 2:
                audio_chain = f';\\\n[0:a][1:a]acrossfade=d={clips[1].config["transition_fade_duration"]}:c1=tri:c2=tri[a1]'
                audio_map = '-map "[a1]"'
            else:
                audio_chain = f';\\\n[0:a][1:a]acrossfade=d={clips[1].config["transition_fade_duration"]}:c1=tri:c2=tri[a1]'

        final_idx = 0
        if len(clips) == 2:
            ffmpeg_cmd += '[0:v][1:v]xfade=transition=%s:duration=%f:offset=%f[v]%s" -map "[v]" %s'\
                        % (clips[1].config['transition_effect'],
                            clips[1].config['transition_fade_duration'],
                            clips[0].file_duration() - clips[1].config['transition_fade_duration'],
                            audio_chain,
                            audio_map)
            dur = clips[0].file_duration() + clips[1].file_duration() - clips[1].config['transition_fade_duration']
        else:
            ffmpeg_cmd += '[0][1]xfade=transition=%s:duration=%f:offset=%f[v1] %s;\\\n'\
                    % (clips[1].config['transition_effect'],
                        clips[1].config['transition_fade_duration'],
                        clips[0].file_duration() - clips[1].config['transition_fade_duration'],
                        audio_chain)

            dur = clips[0].file_duration() + clips[1].file_duration() - clips[1].config['transition_fade_duration']

            for i in range(1, len(clips)-1):
                audio_chain = ''
                if max_audio_streams > 1:
                    for j in range(max_audio_streams):
                        audio_chain += f';\\\n[a{i}-{j}][{i+1}:a:{j}]acrossfade=d={clips[i+1].config["transition_fade_duration"]}:c1=tri:c2=tri[a{i+1}-{j}]'
                else:
                    audio_chain = f';\\\n[a{i}][{i+1}:a]acrossfade=d={clips[i+1].config["transition_fade_duration"]}:c1=tri:c2=tri[a{i+1}]'

                ffmpeg_cmd += '[v%d][%d]xfade=transition=%s:duration=%f:offset=%f[v%d] %s' %\
                            (i,
                            i+1,
                            clips[i+1].config['transition_effect'],
                            clips[i+1].config['transition_fade_duration'],
                            dur - clips[i+1].config['transition_fade_duration'],
                            i+1,
                            audio_chain)
                dur += clips[i+1].file_duration() - clips[i+1].config['transition_fade_duration']
                final_idx = i + 1

                if i != len(clips)-2:
                    ffmpeg_cmd += ';\\\n'

            audio_map = ''
            if max_audio_streams > 1:
                for j in range(max_audio_streams):
                    audio_map += f' -map "[a{final_idx}-{j}]"'
            else:
                audio_map = f' -map "[a{final_idx}]"'

            ffmpeg_cmd += f'" -map "[v{final_idx}]" {audio_map}'
    else:
        # find the maximum number of audio streams in all clips
        filter_complex = ' -filter_complex "'
        if max_audio_streams > 1:
            for i in range(len(clips)):
                filter_complex += '[%d:v]' % i
                audio_streams = 0
                for j in range(clips[i].num_audio_streams):
                    filter_complex += '[%d:a:%d]' % (i, j)
                    audio_streams += 1
            filter_complex += 'concat=n=%d:v=1:a=%d[outv]' % (len(clips), audio_streams)
            map_audio = ' -map "[outv]"'
            for i in range(audio_streams):
                filter_complex += f'[outa{i}]'
                map_audio += f' -map "[outa{i}]"'
            filter_complex += f'"{map_audio}'
        else:
            filter_complex += 'concat=n=%d:v=1:a=1[out]" -map "[out]"' % len(clips)
        ffmpeg_cmd += filter_complex

    ffmpeg_cmd += ' -c:v libx264 -profile:v baseline -pix_fmt yuv420p -preset veryfast'
    if video_bitrate:
        ffmpeg_cmd += ' -b:v ' + str(video_bitrate)
    else:
        ffmpeg_cmd += f' -crf {CRF_OUTPUT_VIDEO}'

    if audio_bitrate:
        ffmpeg_cmd += ' -c:a aac -b:a ' + str(audio_bitrate)
    else:
        ffmpeg_cmd += f'  -c:a aac -b:a {AUDIO_BITRATE_DEFAULT} '

    ffmpeg_cmd += f' {mp4_file}'

    return ffmpeg_cmd

def process_encode_final(clips, clip_params, is_comp, encoding_params):
    mp4_filename = 'output.mp4'
    xml_filename = 'output.xml'

    if is_comp:
        ffmpeg_cmd = merge_all_videos(clips, mp4_filename, clip_params, encoding_params.get('video_bitrate'), encoding_params.get('audio_bitrate'))
        tpc = time.perf_counter()
        run_and_log(f'ffmpeg -hide_banner -progress progress-log.txt -loglevel warning -y {ffmpeg_cmd}', shell=True)
        #log.info(f'Final video encoded in {time.perf_counter() - tpc:.2f} seconds.)
    else:
        single_clip_filename = 'video/0.mp4'
        os.rename(single_clip_filename, mp4_filename)
        #log.info(f'Single clip moved to {mp4_filename}')

    return mp4_filename, xml_filename

def verify_file(filename):
    return filename and os.path.exists(filename) and os.path.getsize(filename) > 0

def main():
    global_start_time = time.perf_counter()
    mp4_filename = None
    success = False
    
    try:
        user_options()
        config = open_config()
        encoding_params = config.get('encoding_parameters', {})
        clip_params = config.get('clip_parameters', {})
        
        #log_initial_params(config, encoding_params, clip_params)
        video_h, video_w, fps, clips, is_comp = process_clips(config, clip_params, encoding_params)

        mp4_filename, xml_filename = process_encode_final(clips, clip_params, is_comp, encoding_params)
        print("812")
        if verify_file(mp4_filename):
            success = True
        else:
            #log.error('Failed to create a valid mp4 file.')
            print('Failed to create valid mp4 file.')
        
    except Exception as e:
        # log.error(f'An error has occured: {e}')
        print(f'An error has occured: {e}')
    finally:

        global_end_time = time.perf_counter()
        #log.info(f'[reels] Total time taken for entire process: {global_end_time - global_start_time:.2f} seconds.')
        print(f'[reels] Total time taken for entire process: {global_end_time - global_start_time:.2f} seconds.')

        if success:
            report_exit('Successfully completed entire process', success=True)
        else:
            report_exit('Failed to compelete entire process', success=False)

if __name__ == '__main__':
    main()

