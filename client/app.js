let janus = null;
let videoroom = null;
let myroom = 1234;  // Match with your videoroom config
let myusername = "user" + Janus.randomString(10);
let localStream = null;
let myid = null;  // Add this to store our publisher ID

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
            console.log("Janus initialized");
            janus = new Janus({
                server: 'ws://localhost:8188/janus',
                iceServers: [], // Empty array for local-only connections
                ipv6: false,    // Disable IPv6
                withCredentials: false,
                success: function() {
                    console.log("Connected to Janus gateway");
                    janus.attach({
                        plugin: "janus.plugin.videoroom",
                        success: function(pluginHandle) {
                            console.log("Plugin attached! (" + pluginHandle.getPlugin() + ", id=" + pluginHandle.getId() + ")");
                            videoroom = pluginHandle;
                            
                            // Join the video room
                            videoroom.send({
                                message: {
                                    request: "join",
                                    room: myroom,
                                    ptype: "publisher",
                                    display: myusername,
                                    secret: "adminpwd123"
                                }
                            });
                        },
                        onmessage: function(msg, jsep) {
                            console.log("Got message:", msg);
                            if (msg["videoroom"] === "joined") {
                                console.log("Successfully joined as publisher", msg);
                                myid = msg["id"];
                                publishOwnFeed();
                            } else if (msg["videoroom"] === "event") {
                                if (msg["configured"] === "ok") {
                                    console.log("Publisher configured, setting up RTP forwarding");
                                    if (!myid) {
                                        console.error("No publisher ID available!");
                                        return;
                                    }
                                    // Now that we're published, set up RTP forwarding
                                    videoroom.send({
                                        message: {
                                            request: "rtp_forward",
                                            room: myroom,
                                            publisher_id: myid,
                                            host: "video_processor",
                                            port: 6002,
                                            audio_port: 0,
                                            video_port: 6002,
                                            video_pt: 96,
                                            video_codec: "vp8",
                                            secret: "adminpwd123"
                                        }
                                    });
                                    $('#status').text("Stream configured, setting up processing");
                                } else if (msg["rtp_forward"] === "ok") {
                                    console.log("RTP forwarding configured, subscribing to processed feed");
                                    $('#status').text("RTP forwarding configured, subscribing...");
                                    subscribeToProcessedFeed();
                                } else if (msg["publishers"]) {
                                    console.log("Got publishers:", msg["publishers"]);
                                    let list = msg["publishers"];
                                    for(let publisher of list) {
                                        if(publisher["id"] !== myid) {
                                            console.log("Found processed feed, subscribing...");
                                            let subscribe = {
                                                request: "join",
                                                room: myroom,
                                                ptype: "subscriber",
                                                feed: publisher["id"],
                                                private_id: 123
                                            };
                                            videoroom.send({message: subscribe});
                                        }
                                    }
                                }
                            }
                            if (jsep) {
                                console.log("Got jsep:", jsep);
                                videoroom.handleRemoteJsep({ jsep: jsep });
                            }
                        },
                        onlocalstream: function(stream) {
                            console.log("Got local stream in Janus", stream);
                        },
                        onremotestream: function(stream) {
                            console.log("Got remote stream", stream);
                            let video = $('#remoteVideo').get(0);
                            video.srcObject = stream;
                            video.play().catch(function(error) {
                                console.error("Error playing remote video:", error);
                            });
                        },
                        error: function(error) {
                            console.error("Error in videoroom plugin:", error);
                            $('#status').text("Error in video room: " + error);
                        },
                        oncleanup: function() {
                            console.log("Got cleanup notification");
                        },
                        destroyed: function() {
                            console.log('destroyed');
                        }
                    });
                },
                error: function(error) {
                    console.error("Error creating Janus instance:", error);
                    $('#status').text("Error connecting to Janus: " + error);
                }
            });
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