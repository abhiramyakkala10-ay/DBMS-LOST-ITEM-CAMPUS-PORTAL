"""
scan_clip.py  — YOLOv8 object detection on a CCTV clip.
Results are stored back into CCTVEvents.detections (JSON column).

Usage:
    python scan_clip.py --clip clips/CAM_01_20250317_143000.mp4 --category bag
    python scan_clip.py --event-id 3 --category phone   # by DB event ID
"""
import os, sys, json, argparse, datetime

sys.path.insert(0, os.path.dirname(__file__))

# Map portal categories → COCO class names (YOLOv8 default)
CATEGORY_MAP = {
    'bag':       ['backpack', 'handbag', 'suitcase'],
    'bottle':    ['bottle'],
    'phone':     ['cell phone'],
    'umbrella':  ['umbrella'],
    'book':      ['book'],
    'laptop':    ['laptop'],
    'wallet':    ['wallet'],
    'keys':      ['key'],          # not a COCO class but included for completeness
    'glasses':   ['glasses'],
    'headphones':['headphones'],
}

def scan_clip(clip_path: str, target_category: str, sample_fps: int = 1) -> list:
    """
    Returns a list of detection dicts:
      [{ frame, timestamp_sec, label, confidence }, ...]
    """
    try:
        from ultralytics import YOLO
        import cv2
    except ImportError:
        print("[ERROR] Install dependencies: pip install ultralytics opencv-python")
        return []

    if not os.path.exists(clip_path):
        print(f"[ERROR] Clip not found: {clip_path}")
        return []

    model          = YOLO('yolov8n.pt')   # downloads automatically on first run
    target_classes = CATEGORY_MAP.get(target_category.lower(), [])
    detections     = []

    cap      = cv2.VideoCapture(clip_path)
    fps      = cap.get(cv2.CAP_PROP_FPS) or 20
    interval = max(1, int(fps / sample_fps))
    frame_no = 0

    print(f"[SCAN] {clip_path}  |  target={target_category}  |  classes={target_classes}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_no % interval == 0:
            results = model(frame, verbose=False)
            for r in results:
                for box, cls, conf in zip(r.boxes.xyxy, r.boxes.cls, r.boxes.conf):
                    label = model.names[int(cls)]
                    # Include if matches target OR if no target specified
                    if not target_classes or label in target_classes:
                        detections.append({
                            'frame':         frame_no,
                            'timestamp_sec': round(frame_no / fps, 2),
                            'label':         label,
                            'confidence':    round(float(conf), 3),
                            'bbox':          [round(float(v), 1) for v in box.tolist()]
                        })

        frame_no += 1

    cap.release()
    print(f"[DONE] {len(detections)} detections found")
    return detections


def scan_and_store(event_id: int, target_category: str):
    """Scan a clip by CCTVEvent ID and persist results to DB."""
    from app import app, db
    from models import CCTVEvent

    with app.app_context():
        event = CCTVEvent.query.get(event_id)
        if not event:
            print(f"[ERROR] CCTVEvent {event_id} not found")
            return

        results = scan_clip(event.clip_path, target_category)
        event.detections = results
        db.session.commit()
        print(f"[DB] Stored {len(results)} detections for event {event_id}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--clip',       help='Direct path to clip file')
    parser.add_argument('--event-id',   type=int, help='CCTVEvent.event_id in DB')
    parser.add_argument('--category',   default='', help='Portal category (bag, phone, etc.)')
    args = parser.parse_args()

    if args.event_id:
        scan_and_store(args.event_id, args.category)
    elif args.clip:
        results = scan_clip(args.clip, args.category)
        print(json.dumps(results, indent=2))
    else:
        parser.print_help()
