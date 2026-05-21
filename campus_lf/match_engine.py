"""
Auto-matching engine.
Strategy: SQL + simple scoring on category, location proximity, and date window.
"""
from models import db, Item, Match
from datetime import timedelta

CATEGORY_WEIGHT  = 0.5
LOCATION_WEIGHT  = 0.3
DATE_WEIGHT      = 0.2

def compute_matches(item_id: int):
    item = Item.query.get(item_id)
    if not item:
        return

    opposite_type = 'found' if item.type == 'lost' else 'lost'

    # Candidate pool: same category, within 14 days, status open
    candidates = Item.query.filter(
        Item.type        == opposite_type,
        Item.category    == item.category,
        Item.status      == 'open',
        Item.date.between(item.date - timedelta(days=14),
                          item.date + timedelta(days=14))
    ).all()

    for cand in candidates:
        score = 0.0

        # Category: already filtered — full points
        score += CATEGORY_WEIGHT

        # Location
        if item.location_id and cand.location_id:
            if item.location_id == cand.location_id:
                score += LOCATION_WEIGHT
            else:
                # Same zone partial credit
                if item.location and cand.location:
                    if item.location.zone == cand.location.zone:
                        score += LOCATION_WEIGHT * 0.5

        # Date proximity: closer = higher score
        delta_days = abs((item.date - cand.date).days)
        if delta_days == 0:
            score += DATE_WEIGHT
        elif delta_days <= 1:
            score += DATE_WEIGHT * 0.8
        elif delta_days <= 3:
            score += DATE_WEIGHT * 0.5
        elif delta_days <= 7:
            score += DATE_WEIGHT * 0.2

        # Determine lost/found ordering
        lost_id  = item.item_id  if item.type == 'lost'  else cand.item_id
        found_id = item.item_id  if item.type == 'found' else cand.item_id

        existing = Match.query.filter_by(lost_item_id=lost_id, found_item_id=found_id).first()
        if existing:
            existing.score = max(existing.score, score)
        else:
            m = Match(lost_item_id=lost_id, found_item_id=found_id, score=round(score, 3))
            db.session.add(m)

    db.session.commit()
