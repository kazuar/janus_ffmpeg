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
c=IN IP4 172.19.0.2
t=0 0
m=video 6002 RTP/AVP 96
a=rtpmap:96 VP8/90000
a=sendonly
a=rtcp-mux
a=framerate:30
a=fmtp:96 max-fr=30;max-fs=3600
a=width:640
a=height:360
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
        '-map', '0:v:0',  # Explicitly map video stream
        '-c:v', 'copy',
        '-bsf:v', 'vp8_metadata,dump_extra',  # Add bitstream filters
        '-f', 'rtp',
        '-payload_type', '96',
        '-ssrc', '1234',
        '-sdp_file', 'output.sdp',  # Generate output SDP
        'rtp://janus:8004?pkt_size=1200'
    ]

    try:
        # Start input process
        input_process = subprocess.Popen(
            input_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )
        
        logging.info("FFmpeg process started successfully")
        
        # Monitor the process
        def log_stderr(process, name):
            while True:
                line = process.stderr.readline()
                if not line:
                    break
                line = line.decode('utf-8', errors='ignore').strip()
                if line and not line.startswith('frame='):
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
