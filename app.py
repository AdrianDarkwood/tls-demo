import os
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
from models import db, Paste

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Replace your database configuration section with this:
if os.environ.get('RENDER'):
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set for production")
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url.replace('postgres://', 'postgresql://', 1)
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pastes.db'

db.init_app(app)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        content = request.form['content']
        device_name = request.form['device_name']
        expiry_minutes = int(request.form['expiry_minutes'])
        max_views = int(request.form['max_views'])
        
        paste_id = secrets.token_hex(4)
        expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        new_paste = Paste(
            id=paste_id,
            content=content,
            device_name=device_name,
            expires_at=expires_at,
            max_views=max_views
        )
        
        db.session.add(new_paste)
        db.session.commit()
        
        return redirect(url_for('view_paste', paste_id=paste_id))
    
    return render_template('index.html')

@app.route('/paste/<paste_id>')
def view_paste(paste_id):
    paste = Paste.query.get_or_404(paste_id)
    now = datetime.utcnow()
    
    expired = False
    if paste.expires_at and paste.expires_at < now:
        expired = True
    if paste.max_views and paste.view_count >= paste.max_views:
        expired = True
    
    if not expired:
        paste.view_count += 1
        db.session.commit()
    
    return render_template('paste.html',
                         paste_id=paste_id,
                         content=paste.content,
                         device_name=paste.device_name,
                         expires_at=paste.expires_at,
                         now=now,
                         view_count=paste.view_count,
                         max_views=paste.max_views,
                         expired=expired)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form['password']
        if check_password_hash(admin_password_hash, password):
            pastes = Paste.query.order_by(Paste.created_at.desc()).all()
            return render_template('admin.html', pastes=pastes, current_time=datetime.utcnow())
        else:
            return render_template('admin_login.html', error="Incorrect password")
    return render_template('admin_login.html')

@app.route('/delete/<paste_id>')
def delete_paste(paste_id):
    paste = Paste.query.get_or_404(paste_id)
    db.session.delete(paste)
    db.session.commit()
    return redirect(url_for('admin'))

def create_app():
    with app.app_context():
        db.create_all()
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)