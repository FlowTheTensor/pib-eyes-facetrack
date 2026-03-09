#!/bin/bash
set -e

XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/1000}
WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-0}

if docker ps -a --format '{{.Names}}' | grep -qx 'ros-camera'; then
  docker stop ros-camera >/dev/null 2>&1 || true
fi

XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR} WAYLAND_DISPLAY=${WAYLAND_DISPLAY} docker compose up --build
