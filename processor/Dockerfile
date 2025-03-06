FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    yasm \
    git \
    wget \
    nasm \
    cmake \
    libx264-dev \
    libx265-dev \
    libvpx-dev \
    libmp3lame-dev \
    libopus-dev \
    python3 \
    python3-pip \
    libsm6 \
    libxext6 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory for build
WORKDIR /tmp

# Build libaom from source
RUN git clone https://aomedia.googlesource.com/aom && \
    mkdir aom_build && \
    cd aom_build && \
    cmake ../aom \
        -DENABLE_TESTS=0 \
        -DENABLE_TOOLS=0 \
        -DENABLE_DOCS=0 \
        -DENABLE_EXAMPLES=0 && \
    make -j$(nproc) && \
    make install && \
    ldconfig

# Download and compile FFmpeg
RUN wget https://ffmpeg.org/releases/ffmpeg-7.1.1.tar.bz2 && \
    tar xjf ffmpeg-7.1.1.tar.bz2 && \
    cd ffmpeg-7.1.1 && \
    ./configure \
        --enable-gpl \
        --enable-libx264 \
        --enable-libx265 \
        --enable-libvpx \
        --enable-libmp3lame \
        --enable-libopus \
        --enable-shared \
        --enable-nonfree \
        --enable-pic \
        --enable-pthreads \
        --enable-hardcoded-tables \
        --disable-debug \
        --disable-doc \
        --enable-libaom && \
    make -j$(nproc) && \
    make install && \
    ldconfig

# Clean up build files
RUN rm -rf /tmp/*

WORKDIR /app

# Create a non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy the rest of the application
COPY video_processor.py .
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Run with unbuffered output for immediate logging
CMD ["python3", "video_processor.py"] 