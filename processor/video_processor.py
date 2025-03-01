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
a=framerate:30
a=imageattr:96 recv [x=[320:1920],y=[240:1080]] send [x=[320:1920],y=[240:1080]]
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
        '-buffer_size', '10M',
        '-i', 'input.sdp',
        '-filter_complex', '[0:v]scale=w=1280:h=720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p[v]',
        '-map', '[v]',
        '-c:v', 'libvpx',
        '-b:v', '1M',
        '-deadline', 'realtime',
        '-cpu-used', '8',
        '-auto-alt-ref', '0',
        '-lag-in-frames', '0',
        '-error-resilient', '1',
        '-keyint_min', '30',
        '-g', '30',
        '-bufsize', '2M',
        '-rc_lookahead', '0',
        '-quality', 'realtime',
        '-max_muxing_queue_size', '1024',
        '-max_delay', '0',
        '-fflags', 'nobuffer+discardcorrupt+fastseek',
        '-flags', 'low_delay',
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
            consecutive_errors = 0
            while True:
                line = process.stderr.readline()
                if not line:
                    break
                line = line.decode('utf-8', errors='ignore').strip()
                if line:
                    if 'error' in line.lower() or 'could not' in line.lower():
                        consecutive_errors += 1
                        logging.error(f"{name} FFmpeg error: {line}")
                        if consecutive_errors > 10:
                            logging.error("Too many consecutive errors, restarting...")
                            process.terminate()
                            break
                    else:
                        consecutive_errors = 0
                        if 'frame=' in line:  # Log frame processing
                            logging.info(f"{name} FFmpeg processing: {line}")
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
