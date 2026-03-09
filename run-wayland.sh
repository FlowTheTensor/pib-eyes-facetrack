#!/bin/bash
set -e

XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/1000}
WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-0}

for name in ros-camera multirepo-ros-camera-1; do
  if docker ps -a --format '{{.Names}}' | grep -qx "${name}"; then
    docker stop "${name}" >/dev/null 2>&1 || true
    docker rm "${name}" >/dev/null 2>&1 || true
  fi
done

XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR} WAYLAND_DISPLAY=${WAYLAND_DISPLAY} docker compose up --build
