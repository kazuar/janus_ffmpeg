FROM canyan/janus-gateway:latest

RUN apt-get update && apt-get install -y \
    libcurl4-openssl-dev \
    libjansson-dev \
    libmicrohttpd-dev \
    libuv1-dev \
    libopus-dev \
    libvpx-dev \
    libaom-dev \
    ffmpeg \
    rustc \
    cargo

# Copy the configuration files
COPY conf/janus.plugin.videoroom.jcfg /usr/local/etc/janus/
COPY conf/janus.plugin.streaming.jcfg /usr/local/etc/janus/

# Expose ports
EXPOSE 8188
EXPOSE 8088
EXPOSE 8889
EXPOSE 8890
EXPOSE 8891
EXPOSE 10000-10200/udp

CMD ["/usr/local/bin/janus", "-F", "/usr/local/etc/janus"]
