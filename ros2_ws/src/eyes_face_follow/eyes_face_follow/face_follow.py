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
    GL_RGB,
    GL_UNSIGNED_BYTE,
    GLfloat,
    glBegin,
    glClear,
    glClearColor,
    glDisable,
    glDrawPixels,
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
    glWindowPos2d,
    glVertex3f,
)
from OpenGL.GLU import gluNewQuadric, gluPerspective, gluSphere
import rclpy
from rclpy.node import Node

from datatypes.srv import GetCameraImage
from vision_msgs.msg import FaceCoordinates


class CameraClient(Node):
    def __init__(self, service_name):
        super().__init__("eyes_face_follow")
        self._client = self.create_client(GetCameraImage, service_name)
        self._last_face = None
        self._last_face_time = 0.0
        self.create_subscription(
            FaceCoordinates,
            "face_coordinates",
            self._face_callback,
            10,
        )

    def _face_callback(self, msg):
        self._last_face = (msg.x, msg.y, msg.confidence)
        self._last_face_time = time.time()

    def wait_for_service(self, timeout_sec=2.0):
        return self._client.wait_for_service(timeout_sec=timeout_sec)

    def service_is_ready(self):
        return self._client.service_is_ready()

    def fetch_image_base64(self, timeout_sec=0.3):
        request = GetCameraImage.Request()
        future = self._client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout_sec)
        if not future.done():
            return None
        result = future.result()
        if result is None:
            return None
        return result.image_base64

    def get_face_coordinates(self, max_age=0.3):
        if self._last_face is None:
            return None
        if time.time() - self._last_face_time > max_age:
            return None
        return self._last_face


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
        self.background_enabled = False
        self.background_frame = None
        self.text_enabled = True
        self.text_font_size = 60
        self.text_margin = 40
        self.text = (
            "Besuchen Sie unsere Technikerschule fuer Elektrotechnik Schwerpunkt "
            "Kuenstliche Intelligenz im Raum 235 und 238"
        )

        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        os.environ.setdefault("SDL_VIDEODRIVER", "wayland")

        pygame.init()
        pygame.font.init()
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
        self.text_surface = self._render_text_surface()

    def update_gaze(self, target_gx, target_gy, alpha=0.35):
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
        if self.background_enabled and self.background_frame is not None:
            self._draw_background()
        if self.text_enabled:
            self._draw_text()
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

    def set_background(self, frame, faces=None, enabled=False):
        self.background_enabled = enabled
        if not enabled or frame is None:
            self.background_frame = None
            return
        bg = frame
        if faces is not None and len(faces) > 0:
            bg = frame.copy()
            for (x, y, w, h) in faces:
                cv2.rectangle(bg, (x, y), (x + w, y + h), (0, 255, 0), 2)
        bg = cv2.resize(bg, (self.width, self.height))
        bg = cv2.cvtColor(bg, cv2.COLOR_BGR2RGB)
        bg = np.flipud(bg)
        bg = np.fliplr(bg)
        self.background_frame = bg

    def _draw_background(self):
        data = self.background_frame.tobytes()
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glWindowPos2d(0, 0)
        glDrawPixels(self.width, self.height, GL_RGB, GL_UNSIGNED_BYTE, data)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

    def _render_text_surface(self):
        font = pygame.font.Font(None, self.text_font_size)
        max_width = max(100, self.width - (self.text_margin * 2))
        words = self.text.split()
        lines = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)

        line_height = font.get_linesize()
        text_h = line_height * len(lines)
        surface = pygame.Surface((max_width, text_h))
        surface.fill((255, 255, 255))
        for i, line in enumerate(lines):
            text_line = font.render(line, True, (0, 0, 0))
            line_w = text_line.get_width()
            x = int((max_width - line_w) / 2)
            surface.blit(text_line, (x, i * line_height))
        return surface

    def _draw_text(self):
        text_w, text_h = self.text_surface.get_size()
        x = int((self.width - text_w) / 2)
        y = 20
        text_data = pygame.image.tostring(self.text_surface, "RGB", True)
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glWindowPos2d(x, y)
        glDrawPixels(text_w, text_h, GL_RGB, GL_UNSIGNED_BYTE, text_data)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)


def decode_image(image_base64):
    raw = base64.b64decode(image_base64)
    data = np.frombuffer(raw, dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def main():
    rclpy.init()
    node = CameraClient("/get_camera_image")

    eyes = EyesRenderer(fullscreen=True)

    clock = pygame.time.Clock()
    last_request = 0.0
    target_gx = 0.0
    target_gy = 0.0
    deadzone = 0.05
    gaze_scale_x = 0.95
    gaze_scale_y = 0.55
    gaze_step = 0.05
    show_debug = False
    last_frame = None
    use_face_topic = os.getenv("USE_FACE_TOPIC", "1") == "1"
    last_service_warn = 0.0

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_t:
                    eyes.text_enabled = not eyes.text_enabled
                elif event.key == pygame.K_a:
                    eyes.adjust_convergence(-1)
                elif event.key == pygame.K_s:
                    eyes.adjust_convergence(1)
                elif event.key == pygame.K_h:
                    gaze_scale_x = min(1.5, gaze_scale_x + gaze_step)
                elif event.key == pygame.K_j:
                    gaze_scale_x = max(0.1, gaze_scale_x - gaze_step)
                elif event.key == pygame.K_v:
                    gaze_scale_y = min(1.2, gaze_scale_y + gaze_step)
                elif event.key == pygame.K_b:
                    gaze_scale_y = max(0.1, gaze_scale_y - gaze_step)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                show_debug = not show_debug

        now = time.time()
        face_coords = node.get_face_coordinates()
        if use_face_topic and face_coords is not None:
            gx, gy, _conf = face_coords
            if abs(gx) < deadzone:
                gx = 0.0
            if abs(gy) < deadzone:
                gy = 0.0
            target_gx = max(-1.0, min(1.0, gx)) * gaze_scale_x
            target_gy = max(-0.6, min(0.6, gy)) * gaze_scale_y

        if now - last_request > 0.03 and show_debug:
            last_request = now
            if not node.service_is_ready():
                if now - last_service_warn > 5.0:
                    node.get_logger().warn("camera service not available")
                    last_service_warn = now
            else:
                image_base64 = node.fetch_image_base64(timeout_sec=1.0)
                if image_base64:
                    frame = decode_image(image_base64)
                    if frame is not None:
                        last_frame = frame

        eyes.update_gaze(target_gx, target_gy)
        eyes.set_background(last_frame, enabled=show_debug)
        eyes.on_draw()
        clock.tick(eyes.fps)

    pygame.quit()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
