import os
import time

import depthai as dai
import rclpy
from rclpy.node import Node

from vision_msgs.msg import FaceCoordinates


class OakdFacePublisher(Node):
    def __init__(self):
        super().__init__("oakd_face_publisher")
        self.publisher = self.create_publisher(FaceCoordinates, "face_coordinates", 10)

        self.preview_width = int(os.getenv("OAKD_PREVIEW_WIDTH", "300"))
        self.preview_height = int(os.getenv("OAKD_PREVIEW_HEIGHT", "300"))
        self.confidence_threshold = float(os.getenv("OAKD_CONFIDENCE", "0.6"))
        self.blob_path = os.getenv("FACE_BLOB_PATH", "")

        self.pipeline = self._create_pipeline()
        self.device = dai.Device(self.pipeline)
        self.det_queue = self.device.getOutputQueue(name="det", maxSize=4, blocking=False)

    def _create_pipeline(self):
        pipeline = dai.Pipeline()

        cam = pipeline.createColorCamera()
        cam.setPreviewSize(self.preview_width, self.preview_height)
        cam.setInterleaved(False)

        det = pipeline.createMobileNetDetectionNetwork()
        det.setConfidenceThreshold(self.confidence_threshold)
        det.setNumInferenceThreads(2)
        det.input.setBlocking(False)

        blob_path = self._resolve_blob_path()
        det.setBlobPath(blob_path)

        cam.preview.link(det.input)

        xout_det = pipeline.createXLinkOut()
        xout_det.setStreamName("det")
        det.out.link(xout_det.input)

        return pipeline

    def _resolve_blob_path(self):
        if self.blob_path and os.path.exists(self.blob_path):
            return self.blob_path

        try:
            import blobconverter

            return blobconverter.from_zoo(
                name="face-detection-retail-0004",
                shaves=6,
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to resolve face detection blob: {exc}")

    def spin_once(self):
        in_det = self.det_queue.tryGet()
        if in_det is None:
            return

        detections = in_det.detections
        if not detections:
            return

        best = max(detections, key=lambda d: d.confidence)
        x_center = (best.xmin + best.xmax) / 2.0
        y_center = (best.ymin + best.ymax) / 2.0

        msg = FaceCoordinates()
        msg.x = (x_center - 0.5) * 2.0
        msg.y = -((y_center - 0.5) * 2.0)
        msg.confidence = float(best.confidence)
        self.publisher.publish(msg)


def main():
    rclpy.init()
    node = OakdFacePublisher()

    try:
        while rclpy.ok():
            node.spin_once()
            rclpy.spin_once(node, timeout_sec=0.01)
            time.sleep(0.005)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
