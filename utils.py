import json
import logging
import re
import subprocess
import time

#log = logging.getLogger('highlight-reels')

# class VideoMetadata:
#     def __init__(self, video_path) -> None:
#         result = subprocess.run(f'ffprobe -v quiet -print_format json -show_format -show_streams {video_path}', shell=True, stdout=subprocess.PIPE)
#         self.video_metadata = json.loads(result.stdout.decode('utf-8'))

#         for stream in self.video_metadata['streams']:
#             if stream['codec_type'] == 'video':
#                 self.video_width = int(stream["width"])
#                 self.video_height = int(stream["height"])

#                 r_frame_rate = stream['r_frame_rate']
#                 match = re.search(r'(\d+)/(\d+)', r_frame_rate)
#                 if not match:
#                     raise Exception(f'Failed to parse r_frame_rate: {r_frame_rate}')
                
#                 self.video_fps = float(int(match.group(1)) / int(match.group(2)))
#                 self.video_duration = float(stream['duration'])
#                 self.video_n_frames = int(self.video_fps * self.video_duration)

def run_and_log(cmd: [] or str, msg: str = None, shell: bool = False):
    try:
        t_start = time.monotonic()
        # log.info(f'[reels] Cmd to run ({msg}): {" ".join(cmd) if isinstance(cmd, list) else cmd}')
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell)
        stdout, stderr = process.communicate()
        return_code = process.returncode()

        cmd_dur = time.monotonic() - t_start

        if return_code == 0:
            #log.info(f"[reels] Cmd succeeded in {cmd_duration:.3f}s:\n{stdout.decode('utf-8')}")
            print(f"[utils.py] line 40, cmd succeeded {cmd_dur:.3f}s:\n{stdout.decode('utf-8')}")
        else:
            #log.error(f"[reels] Cmd failed in {cmd_duration:.3f}s:\n{stderr.decode('utf-8')}")
            print(f"[utils.py] line 43, cmd failed {cmd_dur:.3f}s:\n{stdout.decode('utf-8')}")

        return return_code
    except Exception:
        #log.exception(f'[reels] Failed to run command: {cmd})
        print(f'[utils.py] line 48, failed to run cmd commmand {cmd}')