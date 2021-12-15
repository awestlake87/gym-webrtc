# Quickstart

This is all very rough, and it's ripped from an experiment I was working on awhile back, so don't judge it too harshly :). It's pretty temperamental and needs some work, but this should serve as a decent starting point.

Install the dependencies with pipenv

```
pipenv install
```

Run the signaling / web server

```
pipenv run python server.py
```

In another terminal, start the webrtc client

```
pipenv run python client.py
```

In Chrome (firefox has had issues with aiortc when I was working on this) open [http://localhost:9999/web/index.html](http://localhost:9999/web/index.html). Press "Start Receive"

Subsequent attempts to "Start Receive" will require you to _both_ restart the webrtc client, and refresh the webpage. The signaling / web server should not need to be restarted for each run. 

> Restarting / refreshing the clients is avoidable and I managed to do it later on in the project, but I ripped this example from a point where it was fairly self-contained and simple to isolate for an example on GitHub.