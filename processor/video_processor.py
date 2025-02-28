import cv2
import numpy as np
import subprocess
import socket
# import ffmpeg

def apply_filter(frame):
    # Example filter - you can modify this
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

def process_video_stream():
    # Input stream configuration - receive RTP from Janus
    input_args = [
        'ffmpeg',
        '-listen', '1',  # Enable listening mode
        '-i', 'rtp://0.0.0.0:6002?pkt_size=1200',  # Changed port to 6002
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
        'rtp://janus:8004'  # Use container name instead of localhost
    ]

    # Start FFmpeg processes
    input_process = subprocess.Popen(input_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output_process = subprocess.Popen(output_args, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        while True:
            # Read raw video frame
            frame_size = 1280 * 720 * 3  # width * height * 3 (BGR)
            raw_frame = input_process.stdout.read(frame_size)
            if not raw_frame:
                # Check for FFmpeg errors
                error = input_process.stderr.read()
                if error:
                    print("FFmpeg input error:", error.decode())
                break

            # Convert to numpy array
            frame = np.frombuffer(raw_frame, np.uint8).reshape(720, 1280, 3)

            # Apply processing
            processed_frame = apply_filter(frame)

            # Send processed frame back
            output_process.stdin.write(processed_frame.tobytes())
            output_process.stdin.flush()

    except Exception as e:
        print(f"Error in video processing: {e}")
    finally:
        input_process.terminate()
        output_process.terminate()

if __name__ == '__main__':
    process_video_stream()
