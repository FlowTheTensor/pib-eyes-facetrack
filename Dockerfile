FROM ros:humble-ros-base

SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get install --no-install-recommends -y \
    python3-pip \
    python3-opencv \
    python3-pygame \
    python3-numpy \
    python3-colcon-common-extensions \
    ros-humble-rosidl-default-generators \
    libegl1-mesa \
    libgl1-mesa-dri \
    libgl1-mesa-glx \
    libglu1-mesa \
    && rm -rf /var/lib/apt/lists/*

RUN pip install PyOpenGL

WORKDIR /app

COPY ros2_ws /app/ros2_ws
COPY run.sh /app/run.sh

RUN source /opt/ros/humble/setup.bash && \
    cd /app/ros2_ws && \
    colcon build

RUN chmod +x /app/run.sh

ENV PYTHONUNBUFFERED=1

CMD ["/app/run.sh"]
