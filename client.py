import argparse
import asyncio
import logging
import math

import socketio
from av import VideoFrame

from aiortc import (
    RTCIceCandidate,
    RTCPeerConnection,
    RTCSessionDescription,
    VideoStreamTrack
)
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder
from aiortc.contrib.signaling import BYE
from aiortc.sdp import candidate_from_sdp, candidate_to_sdp

import gym


def object_from_json(message):
    print("got ", message)
    if message["type"] in ["answer", "offer"]:
        return RTCSessionDescription(**message)
    elif message["type"] == "candidate" and message["candidate"]:
        if len(message["candidate"]["candidate"]) != 0:
            candidate = candidate_from_sdp(message["candidate"]["candidate"])
            candidate.sdpMid = message["candidate"]["sdpMid"]
            candidate.sdpMLineIndex = message["candidate"]["sdpMLineIndex"]
            return candidate
        else:
            return None
    elif message["type"] == "bye":
        return BYE


def object_to_json(obj):
    if isinstance(obj, RTCSessionDescription):
        message = {"sdp": obj.sdp, "type": obj.type}
    elif isinstance(obj, RTCIceCandidate):
        message = {
            "type": "candidate",
            "candidate": {
                "candidate": candidate_to_sdp(obj),
                "sdpMid": obj.sdpMid,
                "sdpMLineIndex": obj.sdpMLineIndex
            }
        }
    else:
        assert obj is BYE
        message = {"type": "bye"}

    return message


class Ready:
    pass


class Signaling:
    def __init__(self):
        sio = socketio.AsyncClient()
        self.queue = asyncio.Queue()

        @ sio.on("data")
        async def on_data(data):
            obj = object_from_json(data)
            if obj is not None:
                await self.queue.put(obj)

        @sio.on("ready")
        async def on_ready():
            await self.queue.put(Ready())

        self.sio = sio

    async def connect(self, host, port):
        await self.sio.connect("http://{}:{}".format(host, port))

    async def send(self, data):
        await self.sio.emit("data", object_to_json(data))

    async def receive(self):
        return await self.queue.get()

    async def close(self):
        pass

class GymVideoStreamTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()  # don't forget this!

        self.last_frame = None
        self.frame_queue = asyncio.Queue(10)

    async def put_frame(self, frame):
        await self.frame_queue.put(VideoFrame.from_ndarray(frame))

    async def recv(self):
        if self.last_frame is None:
            frame = await self.frame_queue.get()

        else:
            try:
                frame = self.frame_queue.get_nowait()

            except asyncio.QueueEmpty:
                frame = self.last_frame

        pts, time_base = await self.next_timestamp()

        frame.pts = pts
        frame.time_base = time_base
        self.last_frame = frame
        return frame


async def run_gym_env(video_track):
    ENV = "Breakout-v0"
    print("make {}".format(ENV))
    env = gym.make(ENV)
    print("reset {}".format(ENV))
    obs = env.reset()

    while True:
        img = env.render(mode="rgb_array")

        await video_track.put_frame(img)

        action = env.action_space.sample()  # your agent here (this takes random actions)
        obs, reward, done, info = env.step(action)

        if done:
            obs = env.reset()

    env.close()


async def run(host, port, pc, video_track, recorder, signaling):
    await signaling.connect(host, port)

    def add_tracks():
        pc.addTrack(video_track)

    while True:
        obj = await signaling.receive()

        if isinstance(obj, Ready):
            print("ready")
            add_tracks()
            await pc.setLocalDescription(await pc.createOffer())
            await signaling.send(pc.localDescription)

        elif isinstance(obj, RTCSessionDescription):
            await pc.setRemoteDescription(obj)
            await recorder.start()

            if obj.type == "offer":
                print("received offer")
                # send answer
                add_tracks()
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)
                await signaling.send(pc.localDescription)

        elif isinstance(obj, RTCIceCandidate):
            await pc.addIceCandidate(obj)

        elif obj is BYE:
            print("Exiting")
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--sighost", default="localhost")
    parser.add_argument("--sigport", default=9999)

    args = parser.parse_args()

    video_track = GymVideoStreamTrack()
    recorder = MediaBlackhole()

    pc = RTCPeerConnection()
    signaling = Signaling()

    loop = asyncio.get_event_loop()
    try:
        asyncio.run_coroutine_threadsafe(run_gym_env(video_track), loop)
        loop.run_until_complete(run(
            args.sighost,
            args.sigport,
            pc,
            video_track,
            recorder,
            signaling
        ))

    except KeyboardInterrupt:
        pass

    finally:
        print("stopping recorder")
        loop.run_until_complete(recorder.stop())
        print("closing signaling client")
        loop.run_until_complete(signaling.close())
        print("closing peer connection")
        loop.run_until_complete(pc.close())
        print("done")
