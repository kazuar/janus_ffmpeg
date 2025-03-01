import cv2
import subprocess
import time
import sys
import signal
import logging
import os
import socket
import threading


# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
print("Video processor starting up...")

def set_socket_buffer_size():
    try:
        buffer_size = int(os.environ.get('UDP_BUFFER_SIZE', 26214400))
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, buffer_size)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, buffer_size)
        sock.close()
        logging.info(f"Socket buffer size set to {buffer_size}")
    except Exception as e:
        logging.warning(f"Failed to set socket buffer size: {e}")

def apply_filter(frame):
    # Example filter - you can modify this
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

def create_sdp_file():
    sdp_content = """v=0
o=- 0 0 IN IP4 127.0.0.1
s=Video Processing Stream
c=IN IP4 0.0.0.0
t=0 0
m=video 6002 RTP/AVP 96
a=rtpmap:96 VP8/90000
a=fmtp:96 max-fr=30;max-fs=3600
a=sendrecv
a=rtcp-mux
a=setup:passive
a=mid:video
a=ice-ufrag:video
a=ice-pwd:video123
a=fingerprint:sha-256 D2:B9:31:8F:DF:24:D8:0E:ED:D2:EF:25:9E:AF:6F:B8:34:AE:53:9C:E6:F3:8F:F2:64:15:FA:E8:7F:53:2D:38
"""
    with open('input.sdp', 'w') as f:
        f.write(sdp_content)
    logging.info("Created SDP file for RTP stream")

def process_video_stream():
    logging.info("Starting video processor stream handling...")
    
    set_socket_buffer_size()
    create_sdp_file()
    
    # Input stream configuration
    input_args = [
        'ffmpeg',
        '-hide_banner',
        '-thread_queue_size', '8192',
        '-probesize', '128M',
        '-analyzeduration', '30M',
        '-protocol_whitelist', 'file,rtp,udp',
        '-i', 'input.sdp',
        '-filter_complex', '[0:v]scale=1280:720,format=yuv420p[v]',
        '-map', '[v]',
        '-c:v', 'libvpx',
        '-b:v', '2M',
        '-deadline', 'realtime',
        '-cpu-used', '4',
        '-auto-alt-ref', '0',
        '-keyint_min', '15',
        '-g', '15',
        '-f', 'rtp',
        '-payload_type', '96',
        '-ssrc', '1234',
        '-sdp_file', 'output.sdp',
        f'rtp://janus:6001?pkt_size=1200'
    ]

    try:
        input_process = subprocess.Popen(
            input_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )
        
        logging.info("FFmpeg process started successfully")
        logging.debug(f"FFmpeg command: {' '.join(input_args)}")
        
        # Monitor the process
        def log_stderr(process, name):
            while True:
                line = process.stderr.readline()
                if not line:
                    break
                line = line.decode('utf-8', errors='ignore').strip()
                if line:  # Remove the frame= filter to see all output
                    if 'error' in line.lower() or 'could not' in line.lower():
                        logging.error(f"{name} FFmpeg error: {line}")
                    else:
                        logging.debug(f"{name} FFmpeg: {line}")
        
        # Start monitoring thread
        input_thread = threading.Thread(target=log_stderr, args=(input_process, "Input"))
        input_thread.daemon = True
        input_thread.start()
        
        # Wait for process to complete
        input_process.wait()
        
    except Exception as e:
        logging.error(f"Error in video processing: {e}")
        raise

if __name__ == "__main__":
    logging.info("Video processor starting up...")
    
    def signal_handler(sig, frame):
        logging.info("Shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    while True:
        try:
            process_video_stream()
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
        time.sleep(1)  # Wait before retrying
