import cv2
import numpy as np
import subprocess
import ffmpeg
from flask import Flask, Response

app = Flask(__name__)

def apply_filter(frame):
    # Example filter - you can modify this
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

def process_video_stream():
    # Input stream configuration - receive RTP from Janus
    input_args = [
        'ffmpeg',
        '-i', 'rtp://127.0.0.1:6000',  # Match the videoport in streaming plugin
        '-protocol_whitelist', 'file,rtp,udp',
        '-fflags', 'nobuffer',
        '-flags', 'low_delay',
        '-strict', 'experimental',
        '-c:v', 'vp9',
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        'pipe:'
    ]

    # Output stream configuration - send back to Janus
    output_args = [
        'ffmpeg',
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-s', '1280x720',  # Adjust resolution as needed
        '-r', '30',  # Framerate
        '-i', 'pipe:',
        '-c:v', 'libvpx-vp9',
        '-f', 'rtp',
        '-payload_type', '96',
        'rtp://127.0.0.1:8004'  # Match the port in docker-compose.yml
    ]

    # Start FFmpeg processes
    input_process = subprocess.Popen(input_args, stdout=subprocess.PIPE)
    output_process = subprocess.Popen(output_args, stdin=subprocess.PIPE)

    try:
        while True:
            # Read raw video frame
            frame_size = 1280 * 720 * 3  # width * height * 3 (BGR)
            raw_frame = input_process.stdout.read(frame_size)
            if not raw_frame:
                break

            # Convert to numpy array
            frame = np.frombuffer(raw_frame, np.uint8).reshape(720, 1280, 3)

            # Apply processing
            processed_frame = apply_filter(frame)

            # Send processed frame back
            output_process.stdin.write(processed_frame.tobytes())
            output_process.stdin.flush()

    finally:
        input_process.terminate()
        output_process.terminate()

@app.route('/process')
def video_feed():
    return Response(process_video_stream(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    process_video_stream() 