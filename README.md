# pib-eyes-facetrack

ROS2 Face-Tracking fuer OAK-D Lite, mit Pygame-Augen im Vollbild auf Raspberry Pi 5 (Bookworm, Wayland).

## Voraussetzungen
- Raspberry Pi 5 mit Bookworm (Wayland)
- Docker + Docker Compose
- Kamera-Container wird in diesem Repo mitgebaut (Service `/get_camera_image`)
  - Laeuft im selben ROS2-Graph (via `--network=host`).

## Installation
1) Repo klonen
```bash
git clone <repo-url> ~/pib-eyes-facetrack
cd ~/pib-eyes-facetrack
```

2) Vorbereitung abgeschlossen (der Kamera-Container wird spaeter durch docker compose gebaut)

## Start (Wayland, Vollbild)
Empfohlen (stoppt den alten `ros-camera` automatisch und startet alles):
```bash
bash run-wayland.sh
```

Nach dem Start kannst du den Kamera-Container pruefen:
```bash
ros2 node list
ros2 node info /camera_node
```

Alternativ (manuell):
```bash
docker stop ros-camera
XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 docker compose up --build
```

## Bedienung
- `A` = Augen weiter auseinander
- `S` = Augen mehr zusammen
- `H` = Horizontal staerker
- `J` = Horizontal schwaecher
- `V` = Vertikal staerker
- `B` = Vertikal schwaecher
- Linksklick = Kamera-Background an/aus
- `ESC` = Beenden

## Face-Tracking (Details)
Der Node `face_follow` macht Folgendes:
1) Ruft zyklisch den Service `/get_camera_image` auf.
2) Optional: nutzt `face_coordinates` (schnell, ohne Service-Latenz).
3) Dekodiert das Base64-Bild (JPEG) nach OpenCV fuer den Background.
4) Optionaler Kamera-Background hinter den Augen (per Klick umschaltbar).
5) Findet Gesichter mit Haar-Cascade (`haarcascade_frontalface_default.xml`) wenn kein Topic genutzt wird.
6) Nimmt das groesste Gesicht und berechnet die Blickrichtung relativ zur Bildmitte.
7) Glaettet die Blickrichtung und rendert die Augen im Vollbild.

### Bildrate
Standard: ca. 30+ Hz (Service-Aufruf alle ~0.03 s). Wenn du mehr oder weniger willst, passe die Abfragezeit im Node an.

### Blickrichtung
Die Blickrichtung wird aus der Bildmitte normalisiert:
- `gx = (cx / width - 0.5) * 2`
- `gy = -((cy / height - 0.5) * 2)`

### Tuning
Die Haar-Cascade ist schnell, aber empfindlich auf Licht. Falls noetig:
- Kamera heller/konstanter ausleuchten
- `minSize` im Code vergroessern/verkleinern
- `scaleFactor` und `minNeighbors` anpassen
- Horizontal/Vertikal-Faktor per Tastatur (H/J/V/B)

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

## On-Edge Face Detection (OAK-D Lite)
Der Kamera-Container fuehrt die Gesichtserkennung direkt auf der OAK-D Lite aus
und publiziert die Koordinaten auf dem Topic `face_coordinates`.

Message: `vision_msgs/FaceCoordinates`
- `x` (float32): normalisiert $[-1, 1]$
- `y` (float32): normalisiert $[-1, 1]$
- `confidence` (float32)

### Konfiguration
Die Werte werden ueber Umgebungsvariablen gesetzt (siehe docker-compose.yml):
- `OAKD_FACE_ENABLED` (Standard 1)
- `OAKD_FACE_CONFIDENCE` (Standard 0.6)

### Wechsel zwischen Topic und Service
`eyes-face-follow` nutzt standardmaessig das Topic. Falls du den Service erzwingen willst:
```bash
USE_FACE_TOPIC=0 docker compose up --build
```

## Struktur
- `ros2_ws/src/datatypes`: Service-Definition `GetCameraImage.srv`
- `ros2_ws/src/eyes_face_follow`: ROS2 Node `face_follow` (Service-Client, Face-Detection, Augen-Rendering)
- `ros2_ws/src/vision_msgs`: Message `FaceCoordinates.msg`
- `ros2_ws/src/camera`: OAK-D Lite Kamera-Node mit On-Edge Face Detection
- `Dockerfile`, `Dockerfile.camera`, `docker-compose.yml`, `run-wayland.sh`
