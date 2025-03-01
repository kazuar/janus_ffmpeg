let janus = null;
let videoroom = null;
let myroom = 1234;  // Match with your videoroom config
let myusername = "user" + Janus.randomString(10);
let localStream = null;

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
        debug: true,
        callback: function() {
            console.log("Janus initialized");
            janus = new Janus({
                server: 'ws://localhost:8188/janus',
                ipv6: false,
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
                                    display: myusername
                                }
                            });
                        },
                        onmessage: function(msg, jsep) {
                            console.log("Got message:", msg);
                            if (msg["videoroom"] === "joined") {
                                console.log("Successfully joined room", msg);
                                
                                // After joining, publish our stream
                                publishOwnFeed();
                                
                            } else if (msg["videoroom"] === "event") {
                                if (msg["configured"] === "ok") {
                                    console.log("Publisher configured");
                                } else if (msg["publishers"]) {
                                    console.log("Got publishers:", msg["publishers"]);
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
            videoRecv: true,
            audioSend: false,
            videoSend: true
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