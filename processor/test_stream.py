import subprocess
import time

# Generate a test pattern and stream it via RTP
ffmpeg_cmd = [
    'ffmpeg',
    '-f', 'lavfi',  # Use lavfi input format
    '-i', 'testsrc=size=640x480:rate=30',  # Generate test pattern
    '-c:v', 'libaom-av1',  # Use AV1 codec
    '-b:v', '2M',
    '-deadline', 'realtime',
    '-cpu-used', '4',
    '-f', 'rtp',  # RTP output
    '-payload_type', '45',
    'rtp://localhost:6002?pkt_size=1200'  # Send to video processor port
]

process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

try:
    while True:
        # Print FFmpeg output for debugging
        output = process.stderr.readline().decode()
        if output:
            print(output.strip())
        time.sleep(0.1)
except KeyboardInterrupt:
    process.terminate()
