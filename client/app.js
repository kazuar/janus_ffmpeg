let janus = null;
let videoroom = null;
let myroom = 1234;  // Match with your videoroom config
let myusername = "user" + Janus.randomString(10);

$(document).ready(function() {
    Janus.init({
        debug: true,
        callback: function() {
            janus = new Janus({
                server: 'http://localhost:8088/janus',
                success: function() {
                    janus.attach({
                        plugin: "janus.plugin.videoroom",
                        success: function(pluginHandle) {
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
                            if (msg["videoroom"] === "joined") {
                                // Successfully joined, now publish our stream
                                if ($('#start').prop('disabled')) {
                                    $('#start').removeAttr('disabled');
                                }
                            }
                            if (jsep) {
                                videoroom.handleRemoteJsep({ jsep: jsep });
                            }
                        },
                        onlocalstream: function(stream) {
                            // Show our local stream
                            Janus.attachMediaStream($('#localVideo').get(0), stream);
                        },
                        onremotestream: function(stream) {
                            // Show the processed stream
                            Janus.attachMediaStream($('#remoteVideo').get(0), stream);
                        },
                        error: function(error) {
                            console.error("Error:", error);
                        }
                    });
                }
            });
        }
    });

    $('#start').click(function() {
        navigator.mediaDevices.getUserMedia({video: true, audio: false})
            .then(function(stream) {
                // Publish our stream
                videoroom.createOffer({
                    stream: stream,
                    success: function(jsep) {
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
                        console.error("Error publishing:", error);
                    }
                });
            });
    });
}); 