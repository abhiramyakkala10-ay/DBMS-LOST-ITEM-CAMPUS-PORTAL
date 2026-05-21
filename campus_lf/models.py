from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    user_id   = db.Column(db.Integer, primary_key=True)
    name      = db.Column(db.String(100), nullable=False)
    email     = db.Column(db.String(120), unique=True, nullable=False)
    phone     = db.Column(db.String(15))
    role      = db.Column(db.String(10), default='student')   # student | admin
    password  = db.Column(db.String(200), nullable=False)
    created   = db.Column(db.DateTime, default=datetime.utcnow)

    items      = db.relationship('Item', backref='reporter', lazy=True)
    claims     = db.relationship('Claim', backref='claimant', lazy=True)

class Location(db.Model):
    __tablename__ = 'locations'
    location_id = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    zone        = db.Column(db.String(50))
    has_cctv    = db.Column(db.Boolean, default=False)
    camera_id   = db.Column(db.String(20))

    items       = db.relationship('Item', backref='location', lazy=True)
    cctv_events = db.relationship('CCTVEvent', backref='location', lazy=True)

class Item(db.Model):
    __tablename__ = 'items'
    item_id     = db.Column(db.Integer, primary_key=True)
    type        = db.Column(db.String(10), nullable=False)   # lost | found
    category    = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    image_path  = db.Column(db.String(200))
    location_id = db.Column(db.Integer, db.ForeignKey('locations.location_id'))
    reported_by = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    date        = db.Column(db.DateTime, default=datetime.utcnow)
    status      = db.Column(db.String(20), default='open')   # open | claimed | closed

    claims          = db.relationship('Claim', backref='item', lazy=True)
    matches_lost    = db.relationship('Match', foreign_keys='Match.lost_item_id',  backref='lost_item',  lazy=True)
    matches_found   = db.relationship('Match', foreign_keys='Match.found_item_id', backref='found_item', lazy=True)

class Claim(db.Model):
    __tablename__ = 'claims'
    claim_id    = db.Column(db.Integer, primary_key=True)
    item_id     = db.Column(db.Integer, db.ForeignKey('items.item_id'))
    claimant_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    proof       = db.Column(db.String(200))   # image path of ID proof
    status      = db.Column(db.String(20), default='pending')  # pending | approved | rejected
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow)
    notes       = db.Column(db.Text)

class Match(db.Model):
    __tablename__ = 'matches'
    match_id      = db.Column(db.Integer, primary_key=True)
    lost_item_id  = db.Column(db.Integer, db.ForeignKey('items.item_id'))
    found_item_id = db.Column(db.Integer, db.ForeignKey('items.item_id'))
    score         = db.Column(db.Float, default=0.0)
    verified      = db.Column(db.Boolean, default=False)
    created       = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    __tablename__ = 'notifications'
    notif_id  = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    message   = db.Column(db.Text, nullable=False)
    is_read   = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class CCTVEvent(db.Model):
    __tablename__ = 'cctv_events'
    event_id    = db.Column(db.Integer, primary_key=True)
    camera_id   = db.Column(db.String(20), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.location_id'))
    timestamp   = db.Column(db.DateTime, nullable=False)
    clip_path   = db.Column(db.String(200))
    item_id     = db.Column(db.Integer, db.ForeignKey('items.item_id'), nullable=True)
    detections  = db.Column(db.JSON)   # YOLOv8 results stored as JSON
