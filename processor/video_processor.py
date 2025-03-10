import cv2
import subprocess
import time
import sys
import signal
import logging
import os
import socket
import threading
import numpy as np


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
m=video 6002 RTP/AVPF 45
a=rtpmap:45 AV1/90000
a=fmtp:45 level-idx=5;profile=0;tier=0
a=recvonly
a=framerate:30
a=width:640
a=height:480
"""
    with open('input.sdp', 'w') as f:
        f.write(sdp_content)
    logging.info("Created SDP file for RTP stream")

def process_video_stream():
    logging.info("Starting video processor stream handling...")
    
    set_socket_buffer_size()
    create_sdp_file()
    
    # Input stream configuration
    # Get stream and save to local file
    input_args = [
        'ffmpeg',
        '-hide_banner',
        '-protocol_whitelist', 'file,rtp,udp',
        # '-analyzeduration', '2147483647',  # Maximum analysis duration
        # '-probesize', '2147483647',        # Maximum probe size
        '-c:v', 'libaom-av1',
        '-i', 'input.sdp',
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-video_size', '640x480',
        '-'
    ]

    # Output stream configuration
    output_args = [
        'ffmpeg',
        '-hide_banner',
        '-f', 'rawvideo',
        '-pixel_format', 'bgr24',
        '-video_size', '640x480',
        '-framerate', '30',
        '-i', '-',
        '-c:v', 'libaom-av1',
        '-b:v', '2M',
        '-deadline', 'realtime',
        '-cpu-used', '4',
        '-auto-alt-ref', '0',
        '-lag-in-frames', '0',
        '-error-resilient', '1',
        '-keyint_min', '15',
        '-g', '15',
        '-bufsize', '4M',
        '-rc_lookahead', '10',
        '-quality', 'realtime',
        '-max_muxing_queue_size', '1024',
        '-max_delay', '0',
        '-fflags', 'nobuffer+discardcorrupt+fastseek',
        '-flags', 'low_delay',
        '-force_key_frames', 'expr:gte(t,n_forced*1)',
        '-f', 'rtp',
        '-payload_type', '45',
        '-ssrc', '1234',
        '-sdp_file', 'output.sdp',
        'rtp://janus:6001?pkt_size=1200'
    ]

    try:
        # Start input FFmpeg process
        input_process = subprocess.Popen(
            input_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=100*1024*1024  # 10MB buffer
        )
        
        # Start output FFmpeg process
        output_process = subprocess.Popen(
            output_args,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=100*1024*1024  # 10MB buffer
        )
        
        logging.info("FFmpeg processes started successfully")
        
        # Start error logging threads
        def log_stderr(process, name):
            while True:
                line = process.stderr.readline()
                if not line:
                    break
                line = line.decode('utf-8', errors='ignore').strip()
                if line:
                    if 'error' in line.lower() or 'could not' in line.lower():
                        logging.error(f"{name} FFmpeg error: {line}")
                    else:
                        logging.debug(f"{name} FFmpeg: {line}")
        
        input_thread = threading.Thread(target=log_stderr, args=(input_process, "Input"))
        output_thread = threading.Thread(target=log_stderr, args=(output_process, "Output"))
        input_thread.daemon = True
        output_thread.daemon = True
        input_thread.start()
        output_thread.start()

        # Process frames with OpenCV
        frame_size = 640 * 480 * 3  # width * height * 3 channels (BGR)
        while True:
            # Read raw video frame from input
            raw_frame = input_process.stdout.read(frame_size)
            if not raw_frame:
                logging.warning("No frame data received")
                break
            
            # Print the raw frame size
            print(f"Raw frame size: {len(raw_frame)}")
            
            try:
                # Convert to numpy array for OpenCV
                frame = np.frombuffer(raw_frame, np.uint8).reshape(480, 640, 3)
                
                # Apply more pronounced edge detection
                edges = cv2.Canny(frame, 50, 150)  # Adjusted thresholds
                edges = cv2.dilate(edges, None)  # Make edges thicker
                
                # Create colored edge overlay with brighter color
                colored_edges = np.zeros_like(frame)
                colored_edges[edges > 0] = [0, 255, 0]  # Bright green edges
                
                # Add some visual effects
                blurred = cv2.GaussianBlur(frame, (5, 5), 0)
                sharpened = cv2.addWeighted(frame, 1.5, blurred, -0.5, 0)
                
                # Blend original frame with edges more prominently
                processed_frame = cv2.addWeighted(sharpened, 0.6, colored_edges, 0.4, 0)
                
                # Add text overlay to confirm processing
                cv2.putText(processed_frame, 
                          'Processed Feed', 
                          (50, 50), 
                          cv2.FONT_HERSHEY_SIMPLEX, 
                          1, 
                          (0, 255, 0), 
                          2)
                
                # Ensure frame is in correct format
                if processed_frame.shape != (480, 640, 3):
                    processed_frame = cv2.resize(processed_frame, (640, 480))
                
                # Write processed frame to output
                output_process.stdin.write(processed_frame.tobytes())
                output_process.stdin.flush()
            
            except Exception as e:
                logging.error(f"Error processing frame: {e}")
                continue

    except Exception as e:
        logging.error(f"Error in video processing: {e}")
        raise
    finally:
        # Cleanup
        try:
            input_process.terminate()
            output_process.terminate()
        except:
            pass

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
