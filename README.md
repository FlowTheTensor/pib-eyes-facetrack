# pib-eyes-facetrack

ROS2 Face-Tracking fuer OAK-D Lite, mit Pygame-Augen im Vollbild auf Raspberry Pi 5 (Bookworm, Wayland).

## Voraussetzungen
- Raspberry Pi 5 mit Bookworm (Wayland)
- Docker + Docker Compose
- Laufender Kamera-Container mit ROS2-Service `/get_camera_image`
  - Dieser Container muss im selben ROS2-Graph erreichbar sein (empfohlen: `--network=host`).

## Installation
1) Repo klonen
```bash
git clone <repo-url> ~/pib-eyes-facetrack
cd ~/pib-eyes-facetrack
```

2) Kamera-Container starten (falls nicht laeuft)
- Er muss den Service `/get_camera_image` anbieten.
- Test im Kamera-Container:
```bash
ros2 node list
ros2 node info /camera_node
```

## Start (Wayland, Vollbild)
```bash
XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 docker compose up --build
```

Alternativ:
```bash
bash run-wayland.sh
```

## Bedienung
- `A` = Augen weiter auseinander
- `S` = Augen mehr zusammen
- `ESC` = Beenden

## Face-Tracking (Details)
Der Node `face_follow` macht Folgendes:
1) Ruft zyklisch den Service `/get_camera_image` auf.
2) Dekodiert das Base64-Bild (JPEG) nach OpenCV.
3) Findet Gesichter mit Haar-Cascade (`haarcascade_frontalface_default.xml`).
4) Nimmt das groesste Gesicht und berechnet die Blickrichtung relativ zur Bildmitte.
5) Glaettet die Blickrichtung und rendert die Augen im Vollbild.

### Bildrate
Standard: ca. 10 Hz (Service-Aufruf alle 0.1 s). Wenn du mehr oder weniger willst, passe die Abfragezeit im Node an.

### Blickrichtung
Die Blickrichtung wird aus der Bildmitte normalisiert:
- `gx = (cx / width - 0.5) * 2`
- `gy = -((cy / height - 0.5) * 2)`

### Tuning
Die Haar-Cascade ist schnell, aber empfindlich auf Licht. Falls noetig:
- Kamera heller/konstanter ausleuchten
- `minSize` im Code vergroessern/verkleinern
- `scaleFactor` und `minNeighbors` anpassen

### Kein Gesicht gefunden
Wenn kein Gesicht erkannt wird, bleibt die Blickrichtung stehen und glaettet langsam zur Mitte.

## Troubleshooting
- Kein Fenster sichtbar: nicht mit `-d` starten (kein Vollbild im Hintergrund).
- Service nicht erreichbar: pruefe, ob Kamera-Container mit `--network=host` laeuft.
- Wayland Variablen pruefen:
```bash
echo $XDG_RUNTIME_DIR
echo $WAYLAND_DISPLAY
```

## Struktur
- `ros2_ws/src/datatypes`: Service-Definition `GetCameraImage.srv`
- `ros2_ws/src/eyes_face_follow`: ROS2 Node `face_follow` (Service-Client, Face-Detection, Augen-Rendering)
- `Dockerfile`, `docker-compose.yml`, `run-wayland.sh`
