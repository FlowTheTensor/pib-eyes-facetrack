import base64
import os
import time

import cv2
import numpy as np
import pygame
from pygame.locals import DOUBLEBUF, FULLSCREEN, OPENGL
from OpenGL.GL import (
    GL_AMBIENT_AND_DIFFUSE,
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_FRONT_AND_BACK,
    GL_LIGHT0,
    GL_LIGHTING,
    GL_MODELVIEW,
    GL_POSITION,
    GL_PROJECTION,
    GL_QUAD_STRIP,
    GLfloat,
    glBegin,
    glClear,
    glClearColor,
    glDisable,
    glEnd,
    glEnable,
    glLightfv,
    glLoadIdentity,
    glMaterialfv,
    glMatrixMode,
    glNormal3f,
    glPopMatrix,
    glPushMatrix,
    glTranslatef,
    glVertex3f,
)
from OpenGL.GLU import gluNewQuadric, gluPerspective, gluSphere
import rclpy
from rclpy.node import Node

from datatypes.srv import GetCameraImage


class CameraClient(Node):
    def __init__(self, service_name):
        super().__init__("eyes_face_follow")
        self._client = self.create_client(GetCameraImage, service_name)

    def wait_for_service(self, timeout_sec=2.0):
        return self._client.wait_for_service(timeout_sec=timeout_sec)

    def fetch_image_base64(self, timeout_sec=1.0):
        request = GetCameraImage.Request()
        future = self._client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout_sec)
        if not future.done():
            return None
        result = future.result()
        if result is None:
            return None
        return result.image_base64


class EyesRenderer:
    def __init__(self, width=800, height=480, fullscreen=True, fps=60):
        self.width = width
        self.height = height
        self.fullscreen = fullscreen
        self.fps = fps
        self.start_time = time.time()
        self.blink = 0.0
        self.gx = 0.0
        self.gy = 0.0
        self.focus_distance = 3.0
        self.blink_period = 5.0
        self.blink_duration = 0.25

        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        os.environ.setdefault("SDL_VIDEODRIVER", "wayland")

        pygame.init()
        display_flags = DOUBLEBUF | OPENGL
        if self.fullscreen:
            display_info = pygame.display.Info()
            self.width, self.height = display_info.current_w, display_info.current_h
            display_flags |= FULLSCREEN
        pygame.display.set_mode((self.width, self.height), display_flags)

        gluPerspective(45, self.width / self.height, 0.1, 100.0)
        glTranslatef(0.0, 0.0, -6.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        light_pos = (GLfloat * 4)(0.0, 2.0, 5.0, 1.0)
        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
        glClearColor(1.0, 1.0, 1.0, 1.0)
        self.quadric = gluNewQuadric()

    def update_gaze(self, target_gx, target_gy, alpha=0.2):
        self.gx = (1.0 - alpha) * self.gx + alpha * target_gx
        self.gy = (1.0 - alpha) * self.gy + alpha * target_gy
        self._update_blink()

    def on_draw(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, self.width / self.height, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslatef(0.0, 0.0, -6.0)
        left_gx = self.gx + self._convergence_offset(-1.7)
        right_gx = self.gx + self._convergence_offset(1.7)
        self._draw_eye(-1.7, 0.7, left_gx, self.gy)
        self._draw_eye(1.7, 0.7, right_gx, self.gy)
        pygame.display.flip()

    def _convergence_offset(self, eye_x):
        return max(-1.0, min(1.0, -eye_x / self.focus_distance))

    def _draw_eye(self, cx, cy, gx, gy):
        scale = 1.2
        eyeball_radius = 1.0 * scale
        iris_radius = 0.45 * scale
        pupil_radius = 0.2 * scale
        gaze_scale = 0.35
        iris_x = gx * gaze_scale
        iris_y = gy * gaze_scale
        iris_z = 0.85

        glPushMatrix()
        glTranslatef(cx, cy, 0.0)
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (GLfloat * 4)(0.9, 0.9, 0.9, 1.0))
        gluSphere(self.quadric, eyeball_radius, 40, 40)

        glPushMatrix()
        glTranslatef(iris_x, iris_y, iris_z)
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (GLfloat * 4)(0.35, 0.05, 0.05, 1.0))
        gluSphere(self.quadric, iris_radius, 30, 30)
        glTranslatef(0.0, 0.0, 0.1)
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (GLfloat * 4)(0.0, 0.0, 0.0, 1.0))
        gluSphere(self.quadric, pupil_radius, 20, 20)
        glPopMatrix()

        if self.blink > 0.0:
            lid_color = (GLfloat * 4)(0.8, 0.8, 0.8, 1.0)
            glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, lid_color)
            lid_radius = eyeball_radius * 1.02
            theta = self.blink * (np.pi / 2.0)
            glPushMatrix()
            glTranslatef(0.0, 0.0, eyeball_radius * 0.25)
            glDisable(GL_DEPTH_TEST)
            self._draw_sphere_segment(lid_radius, 0.0, theta)
            self._draw_sphere_segment(lid_radius, np.pi - theta, np.pi)
            glEnable(GL_DEPTH_TEST)
            glPopMatrix()

        glPopMatrix()

    def adjust_convergence(self, direction):
        if direction > 0:
            self.focus_distance = max(2.0, self.focus_distance - 1.0)
        elif direction < 0:
            self.focus_distance = min(100.0, self.focus_distance + 1.0)

    def _update_blink(self):
        t = time.time() - self.start_time
        phase = t % self.blink_period
        if phase < self.blink_duration:
            half = self.blink_duration / 2.0
            self.blink = max(0.0, 1.0 - abs(phase - half) / half)
        else:
            self.blink = 0.0

    def _draw_sphere_segment(self, radius, theta_start, theta_end, slices=36, stacks=12):
        if theta_end <= theta_start:
            return
        for i in range(stacks):
            t0 = theta_start + (theta_end - theta_start) * (i / stacks)
            t1 = theta_start + (theta_end - theta_start) * ((i + 1) / stacks)
            glBegin(GL_QUAD_STRIP)
            for j in range(slices + 1):
                phi = 2.0 * np.pi * (j / slices)
                x0 = np.sin(t0) * np.cos(phi)
                y0 = np.cos(t0)
                z0 = np.sin(t0) * np.sin(phi)
                x1 = np.sin(t1) * np.cos(phi)
                y1 = np.cos(t1)
                z1 = np.sin(t1) * np.sin(phi)
                glNormal3f(x0, y0, z0)
                glVertex3f(radius * x0, radius * y0, radius * z0)
                glNormal3f(x1, y1, z1)
                glVertex3f(radius * x1, radius * y1, radius * z1)
            glEnd()


def decode_image(image_base64):
    raw = base64.b64decode(image_base64)
    data = np.frombuffer(raw, dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def find_face_center(frame, cascade):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=6,
        minSize=(80, 80),
    )
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    cy = y + h * 0.35
    return (x + w / 2.0, cy, frame.shape[1], frame.shape[0])


def main():
    rclpy.init()
    node = CameraClient("/get_camera_image")
    if not node.wait_for_service(timeout_sec=5.0):
        node.get_logger().error("camera service not available")
        rclpy.shutdown()
        return

    eyes = EyesRenderer(fullscreen=True)
    cascade_path = None
    if hasattr(cv2, "data"):
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    else:
        cascade_path = "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(cascade_path)
    if cascade.empty():
        node.get_logger().error(f"Haar cascade not found: {cascade_path}")
        rclpy.shutdown()
        return

    clock = pygame.time.Clock()
    last_request = 0.0
    target_gx = 0.0
    target_gy = 0.0
    face_cx = None
    face_cy = None
    face_alpha = 0.25
    deadzone = 0.05

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_a:
                    eyes.adjust_convergence(-1)
                elif event.key == pygame.K_s:
                    eyes.adjust_convergence(1)

        now = time.time()
        if now - last_request > 0.1:
            last_request = now
            image_base64 = node.fetch_image_base64(timeout_sec=1.0)
            if image_base64:
                frame = decode_image(image_base64)
                if frame is not None:
                    face = find_face_center(frame, cascade)
                    if face:
                        cx, cy, w, h = face
                        if face_cx is None:
                            face_cx = cx
                            face_cy = cy
                        else:
                            face_cx = (1.0 - face_alpha) * face_cx + face_alpha * cx
                            face_cy = (1.0 - face_alpha) * face_cy + face_alpha * cy
                        gx = -((face_cx / w - 0.5) * 2.0)
                        gy = -((face_cy / h - 0.5) * 2.0)
                        if abs(gx) < deadzone:
                            gx = 0.0
                        if abs(gy) < deadzone:
                            gy = 0.0
                        target_gx = max(-1.0, min(1.0, gx)) * 0.7
                        target_gy = max(-0.6, min(0.6, gy)) * 0.4
                    else:
                        target_gx *= 0.9
                        target_gy *= 0.9

        eyes.update_gaze(target_gx, target_gy)
        eyes.on_draw()
        clock.tick(eyes.fps)

    pygame.quit()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
