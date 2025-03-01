# Janus gateway with video processor

This project implements a real-time video processing pipeline using WebRTC, Janus Gateway, and OpenCV. It allows for live video streaming with real-time edge detection and visual effects processing.

## Architecture

The system consists of three main components:
1. **Client** - Web interface for video capture and display
2. **Janus Gateway** - WebRTC server handling video streaming
3. **Video Processor** - Python service that applies real-time video effects

### Flow:
1. Browser captures webcam feed and sends it to Janus
2. Janus forwards the video stream to the video processor via RTP
3. Video processor applies effects and sends processed stream back to Janus
4. Janus delivers the processed stream back to the browser

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/janus-video-processor.git
cd janus-video-processor
```

2. Build and start the Docker containers:
```bash
docker-compose up --build
```

3. Open your browser and navigate to `http://localhost:8080` to access the video processing interface.

## Notes

* Tested only on Macbook Pro with laptop camera and chrome browser.
