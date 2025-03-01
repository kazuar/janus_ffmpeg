let janus = null;
let videoroom = null;
let streaming = null;  // Handle for streaming plugin
let myroom = 1234;
let myusername = "user" + Janus.randomString(10);
let localStream = null;
let myid = null;

$(document).ready(function() {
    // First, check if WebRTC is supported
    if (!Janus.isWebrtcSupported()) {
        alert("No WebRTC support... ");
        return;
    }

    $('#start').click(async function() {
        console.log("Start button clicked");
        try {
            // First get the camera stream and show it locally
            localStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                },
                audio: false
            });
            
            // Show local stream immediately
            let localVideo = $('#localVideo').get(0);
            localVideo.srcObject = localStream;
            await localVideo.play();
            console.log("Local video playing");

            // Then initialize Janus
            initJanus();
            
        } catch (error) {
            console.error("Error getting user media:", error);
            $('#status').text("Error accessing camera: " + error.message);
        }
    });
});

function initJanus() {
    Janus.init({
        debug: "all",
        callback: function() {
            janus = new Janus({
                server: window.SERVER_CONFIG.janus_server,
                success: function() {
                    // Attach to videoroom plugin
                    attachVideoRoom();
                },
                error: function(error) {
                    console.error("Janus error:", error);
                }
            });
        }
    });
}

function attachVideoRoom() {
    janus.attach({
        plugin: "janus.plugin.videoroom",
        success: function(pluginHandle) {
            videoroom = pluginHandle;
            // Join the room with pin
            videoroom.send({
                message: {
                    request: "join",
                    room: 1234,
                    pin: "roompwd123",  // Add room pin
                    ptype: "publisher",
                    display: "User " + Math.round(Math.random() * 100)
                }
            });
        },
        error: function(error) {
            console.error("Error attaching plugin:", error);
        },
        onmessage: function(msg, jsep) {
            console.log("Videoroom message:", msg);
            if (msg["videoroom"] === "joined") {
                myid = msg["id"];
                publishOwnFeed();
            } else if (msg["videoroom"] === "event") {
                if (msg["configured"] === "ok") {
                    // Set up RTP forwarding to video processor
                    videoroom.send({
                        message: {
                            request: "rtp_forward",
                            room: 1234,
                            publisher_id: myid,
                            host: "video_processor",
                            port: 6002,
                            video_port: 6002,
                            video_pt: 96,
                            video_codec: "vp8",
                            secret: "adminpwd123"
                        },
                        success: function(result) {
                            console.log("RTP forwarding setup:", result);
                            // Now attach to streaming plugin
                            setTimeout(attachProcessedStream, 1000);  // Add small delay
                        }
                    });
                }
            }
            if(jsep) {
                videoroom.handleRemoteJsep({jsep: jsep});
            }
        },
        onlocalstream: function(stream) {
            console.log("Got local stream");
            let video = $('#localVideo').get(0);
            video.srcObject = stream;
            video.play().catch(function(error) {
                console.error("Error playing local video:", error);
            });
        }
    });
}

function attachProcessedStream() {
    console.log("Attaching to streaming plugin");
    janus.attach({
        plugin: "janus.plugin.streaming",
        success: function(pluginHandle) {
            streaming = pluginHandle;
            console.log("Streaming plugin attached, watching stream ID 1");
            streaming.send({
                message: {
                    request: "watch",
                    id: 1,
                    offer_video: true,
                    offer_audio: false
                }
            });
        },
        error: function(error) {
            console.error("Error attaching to streaming plugin:", error);
            $('#status').text("Error attaching to streaming plugin: " + error);
        },
        onmessage: function(msg, jsep) {
            console.log("Streaming message:", msg);
            if(jsep) {
                streaming.createAnswer({
                    jsep: jsep,
                    tracks: [
                        { type: 'video', capture: false, recv: true }
                    ],
                    success: function(jsep) {
                        console.log("Got SDP answer:", jsep);
                        streaming.send({
                            message: { request: "start" },
                            jsep: jsep
                        });
                    },
                    error: function(error) {
                        console.error("Error creating answer:", error);
                    }
                });
            }
        },
        onremotetrack: function(track, mid, on) {
            console.log("Got remote track:", track.kind);
            if (track.kind === "video") {
                let video = $('#remoteVideo').get(0);
                if (video.srcObject === null) {
                    video.srcObject = new MediaStream();
                }
                if (on) {
                    video.srcObject.addTrack(track);
                }
            }
        },
        oncleanup: function() {
            console.log("Got a cleanup notification");
            $('#remoteVideo').get(0).srcObject = null;
        }
    });
}

function publishOwnFeed() {
    videoroom.createOffer({
        media: {
            audioRecv: false,
            videoRecv: false,
            audioSend: false,
            videoSend: true,
            video: {
                width: { exact: 1280 },
                height: { exact: 720 },
                codec: "vp8"
            }
        },
        stream: localStream,
        success: function(jsep) {
            console.log("Got publisher SDP:", jsep);
            videoroom.send({
                message: {
                    request: "publish",
                    video: true,
                    audio: false
                },
                jsep: jsep
            });
        },
        error: function(error) {
            console.error("Error creating offer:", error);
            $('#status').text("Error publishing stream: " + error);
        }
    });
}

function subscribeToProcessedFeed() {
    // Create a new handle for subscribing
    janus.attach({
        plugin: "janus.plugin.videoroom",
        success: function(pluginHandle) {
            let subscriber = pluginHandle;
            let subscribe = {
                request: "join",
                room: myroom,
                ptype: "subscriber",
                feed: myid,  // Subscribe to our own processed feed
                private_id: 123
            };
            subscriber.send({message: subscribe});
        },
        error: function(error) {
            console.error("Error attaching subscriber plugin:", error);
        },
        onmessage: function(msg, jsep) {
            console.log("Subscriber got message:", msg);
            if(jsep) {
                subscriber.createAnswer({
                    jsep: jsep,
                    media: { audioSend: false, videoSend: false },
                    success: function(jsep) {
                        let body = { request: "start", room: myroom };
                        subscriber.send({message: body, jsep: jsep});
                    }
                });
            }
        },
        onremotestream: function(stream) {
            console.log("Got processed stream", stream);
            let video = $('#remoteVideo').get(0);
            video.srcObject = stream;
            video.play().catch(function(error) {
                console.error("Error playing processed video:", error);
            });
        }
    });
} 