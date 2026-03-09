#!/bin/bash
set -e

XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/1000}
WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-0}

IMAGE_NAME=eyes-face-follow

docker build -t ${IMAGE_NAME} .

docker run --rm -it \
  --user "$(id -u):$(id -g)" \
  --group-add video \
  --network=host \
  --device=/dev/dri \
  -e HOME=/tmp \
  -e ROS_LOG_DIR=/tmp/ros/log \
  -e XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR} \
  -e WAYLAND_DISPLAY=${WAYLAND_DISPLAY} \
  -e SDL_VIDEODRIVER=wayland \
  -e PYOPENGL_PLATFORM=egl \
  -v ${XDG_RUNTIME_DIR}:${XDG_RUNTIME_DIR} \
  ${IMAGE_NAME}
