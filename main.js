const PC_CONFIG = {}

let socket;

document.getElementById("sigHost").value = window.location.hostname

let connect = (url) => {
    socket = io(url, { autoConnect: false })
    socket.on("data", (data) => {
        console.log("Data received: ", data);
        handleSignalingData(data);
    });

    socket.on("ready", () => {
        console.log("Ready");
        createPeerConnection();
        
        if (localStream) {
            sendOffer();
        }
    });
    socket.connect();
};

let sendData = (data) => {
    socket.emit("data", data);
};

let pc;
let localStream;
let remoteStreamElement = document.querySelector("#remoteStream");

document.getElementById("startCapture").onclick = () => {
    navigator.mediaDevices.getDisplayMedia({ audio: true, video: true })
        .then((stream) => {
            console.log("Stream found");
            localStream = stream;

            connect("http://" + document.getElementById("sigHost").value + ":9999")
        })
        .catch(error => {
            console.error("Stream not found: ", error);
        });
};
document.getElementById("startReceive").onclick = () => {
    connect("http://" + document.getElementById("sigHost").value + ":9999")
};

let createPeerConnection = () => {
    try {
        pc = new RTCPeerConnection(PC_CONFIG);
        pc.onicecandidate = onIceCandidate;
        pc.onaddstream = onAddStream;
        if (localStream) {
            pc.addStream(localStream);
        }
        console.log("PeerConnection created");
    } catch (error) {
        console.error("PeerConnection failed: ", error);
    }
};

let sendOffer = () => {
    console.log("Send offer");
    pc.createOffer().then(
        setAndSendLocalDescription,
        (error) => { console.error("Send offer failed: ", error); }
    );
};

let sendAnswer = () => {
    console.log("Send answer");
    pc.createAnswer().then(
        setAndSendLocalDescription,
        (error) => { console.error("Send answer failed: ", error); }
    )
};

let setAndSendLocalDescription = (sessionDescription) => {
    pc.setLocalDescription(sessionDescription);
    console.log("Local description set");
    sendData(sessionDescription);
};

let onIceCandidate = (event) => {
    if (event.candidate) {
        console.log("ICE candidate");
        sendData({
            type: "candidate",
            candidate: event.candidate
        });
    }
};

let onAddStream = (event) => {
    console.log("Add stream");
    remoteStreamElement.srcObject = event.stream;
};

let handleSignalingData = (data) => {
    switch (data.type) {
        case "offer":
            createPeerConnection();
            pc.setRemoteDescription(new RTCSessionDescription(data));
            sendAnswer();
            break;
        
        case "answer":
            pc.setRemoteDescription(new RTCSessionDescription(data));
            break;
        
        case "candidate":
            pc.addIceCandidate(new RTCIceCandidate(data.candidate));
            break;
    }
};