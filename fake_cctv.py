"""
fake_cctv.py  — Simulates a CCTV camera using the system webcam.
Run this independently to populate the CCTVEvents table with demo clips.

Usage:
    python fake_cctv.py --camera CAM_01 --location 1 --duration 30
"""
import cv2, os, sys, argparse, datetime

sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from models import CCTVEvent, Location

CLIPS_DIR = os.path.join(os.path.dirname(__file__), 'clips')
os.makedirs(CLIPS_DIR, exist_ok=True)

def db_insert_event(camera_id: str, location_id: int, ts: datetime.datetime, clip_path: str):
    with app.app_context():
        event = CCTVEvent(
            camera_id   = camera_id,
            location_id = location_id,
            timestamp   = ts,
            clip_path   = clip_path
        )
        db.session.add(event)
        db.session.commit()
        print(f"[DB] Inserted CCTVEvent: {clip_path}")

def capture_clip(camera_id: str, location_id: int, duration: int = 30, device_index: int = 0):
    cap = cv2.VideoCapture(device_index)
    if not cap.isOpened():
        print(f"[WARN] Camera device {device_index} not available. Generating blank clip.")
        _generate_blank_clip(camera_id, location_id, duration)
        return

    ts       = datetime.datetime.now()
    filename = f"{camera_id}_{ts.strftime('%Y%m%d_%H%M%S')}.mp4"
    filepath = os.path.join(CLIPS_DIR, filename)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out    = cv2.VideoWriter(filepath, fourcc, 20.0, (640, 480))

    print(f"[REC] Recording {duration}s clip -> {filepath}")
    start = datetime.datetime.now()
    while (datetime.datetime.now() - start).seconds < duration:
        ret, frame = cap.read()
        if ret:
            out.write(frame)

    cap.release()
    out.release()
    db_insert_event(camera_id, location_id, ts, filepath)
    print(f"[DONE] Saved: {filepath}")

def _generate_blank_clip(camera_id: str, location_id: int, duration: int = 30):
    """Fallback: create a solid-color clip when no webcam is available."""
    import numpy as np

    ts       = datetime.datetime.now()
    filename = f"{camera_id}_{ts.strftime('%Y%m%d_%H%M%S')}_mock.mp4"
    filepath = os.path.join(CLIPS_DIR, filename)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out    = cv2.VideoWriter(filepath, fourcc, 20.0, (640, 480))
    frame  = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(frame, f"MOCK CAM: {camera_id}", (50, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 200, 100), 2)

    for _ in range(duration * 20):   # 20fps × seconds
        out.write(frame)
    out.release()

    db_insert_event(camera_id, location_id, ts, filepath)
    print(f"[MOCK] Created blank clip: {filepath}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--camera',   default='CAM_01', help='Camera ID')
    parser.add_argument('--location', type=int, default=1, help='Location ID in DB')
    parser.add_argument('--duration', type=int, default=30, help='Clip length in seconds')
    parser.add_argument('--device',   type=int, default=0,  help='Webcam device index')
    args = parser.parse_args()

    with app.app_context():
        db.create_all()

    capture_clip(args.camera, args.location, args.duration, args.device)
