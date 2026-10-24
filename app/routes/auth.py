import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify
)
from werkzeug.security import check_password_hash, generate_password_hash
from app.database import query_db, query_one, insert_db, execute_db
from app.services.audit import log_audit

bp = Blueprint('auth', __name__, url_prefix='/auth')

def login_required(view):
    """Decorator to require login for a view."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get('user_id') is None:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        return view(**kwargs)
    return wrapped_view

def role_required(*allowed_roles):
    """Decorator to require specific roles (e.g. 'staff', 'admin')."""
    def decorator(view):
        @functools.wraps(view)
        def wrapped_view(**kwargs):
            if session.get('user_id') is None:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for('auth.login', next=request.url))
            user_role = session.get('role')
            if user_role not in allowed_roles:
                flash("Access denied: You do not have permissions for this section.", "danger")
                if user_role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif user_role == 'staff':
                    return redirect(url_for('staff.dashboard'))
                else:
                    return redirect(url_for('citizen.dashboard'))
            return view(**kwargs)
        return wrapped_view
    return decorator

@bp.before_app_request
def load_logged_in_user():
    """Load user info into Flask g on every request."""
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = query_one(
            """SELECT u.id, u.email, u.full_name, u.phone, u.role, u.department_id, d.name as department_name 
               FROM users u 
               LEFT JOIN departments d ON u.department_id = d.id 
               WHERE u.id = ?""",
            (user_id,)
        )

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        user = query_one("SELECT * FROM users WHERE LOWER(email) = ?", (email,))
        
        if user is None:
            flash("No account registered with this email address.", "danger")
        elif not check_password_hash(user['password_hash'], password):
            flash("Incorrect password. Please verify and try again.", "danger")
        elif user['is_active'] == 0:
            flash("This account is currently disabled. Please contact municipal support.", "danger")
        else:
            session.clear()
            session['user_id'] = user['id']
            session['email'] = user['email']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            session['department_id'] = user['department_id']
            
            log_audit(user['id'], "LOGIN", "USER", user['id'], f"User logged in ({user['role']})")
            flash(f"Welcome back, {user['full_name']}!", "success")
            
            next_page = request.args.get('next')
            if next_page and not next_page.startswith('/auth'):
                return redirect(next_page)
                
            if user['role'] == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user['role'] == 'staff':
                return redirect(url_for('staff.dashboard'))
            else:
                return redirect(url_for('citizen.dashboard'))
                
    return render_template('public/login.html')

@bp.route('/demo-login/<role>')
def demo_login(role):
    """
    1-Click demonstration login for Innovators Conclave 2026 judges.
    Instantly authenticates as Citizen, Staff, or Administrator.
    """
    demo_emails = {
        'citizen': 'citizen@civicfix.org',
        'staff': 'staff@civicfix.org',
        'sanitation': 'sanitation@civicfix.org',
        'admin': 'admin@civicfix.org'
    }
    
    target_email = demo_emails.get(role, 'citizen@civicfix.org')
    user = query_one("SELECT * FROM users WHERE email = ?", (target_email,))
    
    if user:
        session.clear()
        session['user_id'] = user['id']
        session['email'] = user['email']
        session['full_name'] = user['full_name']
        session['role'] = user['role']
        session['department_id'] = user['department_id']
        
        log_audit(user['id'], "DEMO_LOGIN", "USER", user['id'], f"1-Click Demo Login as {user['role']}")
        flash(f"Logged in as Demo {user['role'].title()}: {user['full_name']}", "info")
        
        if user['role'] == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user['role'] == 'staff':
            return redirect(url_for('staff.dashboard'))
        else:
            return redirect(url_for('citizen.dashboard'))
            
    flash("Demo user record not found. Please run seed_data.py", "danger")
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not full_name or not email or not password:
            flash("All required fields must be filled.", "danger")
        elif len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
        elif password != confirm_password:
            flash("Passwords do not match.", "danger")
        else:
            existing = query_one("SELECT id FROM users WHERE LOWER(email) = ?", (email,))
            if existing:
                flash("An account is already registered with this email address.", "danger")
            else:
                pwd_hash = generate_password_hash(password)
                new_id = insert_db(
                    """INSERT INTO users (email, password_hash, full_name, phone, role)
                       VALUES (?, ?, ?, ?, 'citizen')""",
                    (email, pwd_hash, full_name, phone)
                )
                log_audit(new_id, "REGISTER", "USER", new_id, "New citizen registered")
                
                # Auto log in
                session.clear()
                session['user_id'] = new_id
                session['email'] = email
                session['full_name'] = full_name
                session['role'] = 'citizen'
                session['department_id'] = None
                
                flash(f"Account successfully created! Welcome to CivicFix, {full_name}.", "success")
                return redirect(url_for('citizen.dashboard'))
                
    return render_template('public/register.html')

@bp.route('/logout')
def logout():
    uid = session.get('user_id')
    if uid:
        log_audit(uid, "LOGOUT", "USER", uid, "User logged out")
    session.clear()
    flash("You have been safely signed out.", "info")
    return redirect(url_for('public.index'))
