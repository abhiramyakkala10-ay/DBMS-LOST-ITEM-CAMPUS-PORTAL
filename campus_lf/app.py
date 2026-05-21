from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from models import db, User, Location, Item, Claim, Match, Notification, CCTVEvent
from match_engine import compute_matches
import os, json

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'campus_lf_secret_2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///campus_lf.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ─── AUTH ────────────────────────────────────────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name     = request.form['name']
        email    = request.form['email']
        phone    = request.form.get('phone', '')
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('register'))

        user = User(name=name, email=email, phone=phone,
                    password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.user_id
            session['name']    = user.name
            session['role']    = user.role
            return redirect(url_for('index'))
        flash('Invalid credentials.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─── INDEX ────────────────────────────────────────────────────────────────────

@app.route('/')
@login_required
def index():
    recent_lost  = Item.query.filter_by(type='lost',  status='open').order_by(Item.date.desc()).limit(6).all()
    recent_found = Item.query.filter_by(type='found', status='open').order_by(Item.date.desc()).limit(6).all()
    stats = {
        'lost':    Item.query.filter_by(type='lost').count(),
        'found':   Item.query.filter_by(type='found').count(),
        'claimed': Item.query.filter_by(status='claimed').count(),
        'users':   User.query.count(),
    }
    notifs = Notification.query.filter_by(user_id=session['user_id'], is_read=False).count()
    return render_template('index.html', recent_lost=recent_lost,
                           recent_found=recent_found, stats=stats, notif_count=notifs)

# ─── ITEMS ────────────────────────────────────────────────────────────────────

@app.route('/items')
@login_required
def items():
    item_type = request.args.get('type', 'all')
    category  = request.args.get('category', '')
    q         = request.args.get('q', '')

    query = Item.query.filter_by(status='open')
    if item_type in ('lost', 'found'):
        query = query.filter_by(type=item_type)
    if category:
        query = query.filter_by(category=category)
    if q:
        query = query.filter(Item.description.ilike(f'%{q}%'))

    items = query.order_by(Item.date.desc()).all()
    locations  = Location.query.all()
    categories = db.session.query(Item.category).distinct().all()
    return render_template('items.html', items=items, locations=locations,
                           categories=[c[0] for c in categories],
                           current_type=item_type, current_cat=category, q=q)

@app.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    if request.method == 'POST':
        image_path = None
        if 'image' in request.files:
            f = request.files['image']
            if f and allowed_file(f.filename):
                filename   = secure_filename(f.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                f.save(image_path)

        item = Item(
            type        = request.form['type'],
            category    = request.form['category'],
            description = request.form['description'],
            image_path  = image_path,
            location_id = request.form.get('location_id') or None,
            reported_by = session['user_id'],
            date        = datetime.strptime(request.form['date'], '%Y-%m-%dT%H:%M')
        )
        db.session.add(item)
        db.session.commit()

        # Run auto-match
        compute_matches(item.item_id)

        # Notify user
        n = Notification(user_id=session['user_id'],
                         message=f"Your {item.type} report for '{item.category}' was submitted.")
        db.session.add(n)
        db.session.commit()

        flash('Item reported successfully!', 'success')
        return redirect(url_for('item_detail', item_id=item.item_id))

    locations = Location.query.all()
    return render_template('report.html', locations=locations)

@app.route('/item/<int:item_id>')
@login_required
def item_detail(item_id):
    item = Item.query.get_or_404(item_id)
    # Matches — show the other side
    if item.type == 'lost':
        matches = Match.query.filter_by(lost_item_id=item_id).order_by(Match.score.desc()).all()
    else:
        matches = Match.query.filter_by(found_item_id=item_id).order_by(Match.score.desc()).all()

    # CCTV clips
    clips = []
    if item.location and item.location.has_cctv:
        clips = CCTVEvent.query.filter(
            CCTVEvent.camera_id == item.location.camera_id,
            CCTVEvent.timestamp.between(
                item.date - timedelta(hours=2),
                item.date + timedelta(hours=1)
            )
        ).all()

    user_claim = Claim.query.filter_by(item_id=item_id, claimant_id=session['user_id']).first()
    return render_template('item_detail.html', item=item, matches=matches,
                           clips=clips, user_claim=user_claim)

# ─── CLAIMS ───────────────────────────────────────────────────────────────────

@app.route('/claim/<int:item_id>', methods=['POST'])
@login_required
def claim_item(item_id):
    item = Item.query.get_or_404(item_id)
    if item.reported_by == session['user_id']:
        flash("You can't claim your own report.", 'error')
        return redirect(url_for('item_detail', item_id=item_id))

    proof_path = None
    if 'proof' in request.files:
        f = request.files['proof']
        if f and allowed_file(f.filename):
            filename   = secure_filename(f.filename)
            proof_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            f.save(proof_path)

    claim = Claim(item_id=item_id, claimant_id=session['user_id'],
                  proof=proof_path, notes=request.form.get('notes', ''))
    db.session.add(claim)

    # Notify reporter
    n = Notification(user_id=item.reported_by,
                     message=f"Someone claimed your {item.type} report for '{item.category}'.")
    db.session.add(n)
    db.session.commit()
    flash('Claim submitted! Waiting for admin approval.', 'success')
    return redirect(url_for('item_detail', item_id=item_id))

# ─── MY ITEMS / NOTIFICATIONS ─────────────────────────────────────────────────

@app.route('/my-items')
@login_required
def my_items():
    reported = Item.query.filter_by(reported_by=session['user_id']).order_by(Item.date.desc()).all()
    claims   = Claim.query.filter_by(claimant_id=session['user_id']).all()
    return render_template('my_items.html', reported=reported, claims=claims)

@app.route('/notifications')
@login_required
def notifications():
    notifs = Notification.query.filter_by(user_id=session['user_id']).order_by(Notification.timestamp.desc()).all()
    for n in notifs:
        n.is_read = True
    db.session.commit()
    return render_template('notifications.html', notifs=notifs)

# ─── ADMIN ────────────────────────────────────────────────────────────────────

@app.route('/admin')
@admin_required
def admin():
    items   = Item.query.order_by(Item.date.desc()).limit(20).all()
    claims  = Claim.query.filter_by(status='pending').all()
    matches = Match.query.order_by(Match.score.desc()).limit(10).all()
    return render_template('admin.html', items=items, claims=claims, matches=matches)

@app.route('/admin/claim/<int:claim_id>/<action>')
@admin_required
def admin_claim(claim_id, action):
    claim = Claim.query.get_or_404(claim_id)
    if action == 'approve':
        claim.status       = 'approved'
        claim.item.status  = 'claimed'
        n = Notification(user_id=claim.claimant_id,
                         message=f"Your claim for '{claim.item.category}' was approved!")
    elif action == 'reject':
        claim.status = 'rejected'
        n = Notification(user_id=claim.claimant_id,
                         message=f"Your claim for '{claim.item.category}' was rejected.")
    db.session.add(n)
    db.session.commit()
    flash(f'Claim {action}d.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/cctv/<int:item_id>')
@admin_required
def admin_cctv(item_id):
    item = Item.query.get_or_404(item_id)
    clips = []
    if item.location and item.location.has_cctv:
        clips = CCTVEvent.query.filter(
            CCTVEvent.camera_id == item.location.camera_id,
            CCTVEvent.timestamp.between(
                item.date - timedelta(hours=2),
                item.date + timedelta(hours=1)
            )
        ).all()
    return render_template('cctv_review.html', item=item, clips=clips)

# ─── API (for AJAX) ───────────────────────────────────────────────────────────

@app.route('/api/matches/<int:item_id>')
@login_required
def api_matches(item_id):
    item = Item.query.get_or_404(item_id)
    if item.type == 'lost':
        matches = Match.query.filter_by(lost_item_id=item_id).order_by(Match.score.desc()).all()
        paired  = [{'id': m.found_item_id, 'score': m.score,
                    'description': m.found_item.description,
                    'category': m.found_item.category} for m in matches]
    else:
        matches = Match.query.filter_by(found_item_id=item_id).order_by(Match.score.desc()).all()
        paired  = [{'id': m.lost_item_id, 'score': m.score,
                    'description': m.lost_item.description,
                    'category': m.lost_item.category} for m in matches]
    return jsonify(paired)

# ─── INIT ─────────────────────────────────────────────────────────────────────

def seed_data():
    if Location.query.count() == 0:
        locs = [
            Location(name='Main Gate',    zone='Entry',   has_cctv=True,  camera_id='CAM_01'),
            Location(name='Library',      zone='Block-A', has_cctv=True,  camera_id='CAM_02'),
            Location(name='Canteen',      zone='Block-B', has_cctv=False),
            Location(name='Sports Ground',zone='Outer',   has_cctv=True,  camera_id='CAM_03'),
            Location(name='Hostel Block', zone='Hostel',  has_cctv=True,  camera_id='CAM_04'),
            Location(name='Parking Lot',  zone='Outer',   has_cctv=True,  camera_id='CAM_05'),
        ]
        db.session.add_all(locs)

    if User.query.filter_by(role='admin').count() == 0:
        admin = User(name='Admin', email='admin@vignan.ac.in',
                     password=generate_password_hash('admin123'), role='admin')
        db.session.add(admin)

    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_data()
    app.run(debug=True)
