#!/bin/bash
set -e

source /opt/ros/humble/setup.bash
source /app/ros2_ws/install/setup.bash

exec ros2 run eyes_face_follow face_follow
