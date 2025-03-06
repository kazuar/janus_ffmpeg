FROM canyan/janus-gateway:latest

RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libcurl4-openssl-dev \
    libjansson-dev \
    libmicrohttpd-dev \
    libuv1-dev \
    libopus-dev \
    libvpx-dev \
    # libaom-dev \
    libmp3lame-dev \
    libx264-dev \
    libx265-dev \
    ffmpeg \
    rustc \
    wget \
    bzip2 \
    nasm \
    yasm \
    cmake \
    cargo \
    git \
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
        --enable-libaom \
        --enable-shared && \
    make -j$(nproc) && \
    make install && \
    ldconfig

# Clean up build files
RUN rm -rf /tmp/*

# Copy the configuration files
COPY conf/janus.jcfg /usr/local/etc/janus/
COPY conf/janus.plugin.videoroom.jcfg /usr/local/etc/janus/
COPY conf/janus.plugin.streaming.jcfg /usr/local/etc/janus/

# Expose ports
EXPOSE 8188
EXPOSE 8088
EXPOSE 6002/udp
EXPOSE 6001/udp
EXPOSE 8004/udp
EXPOSE 20000-20050/udp

CMD ["/usr/local/bin/janus", "-F", "/usr/local/etc/janus"]