from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required
from models import db, User
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint("auth", __name__)

from flask import request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from models import db, User

from flask import request, redirect, url_for, flash, render_template
from werkzeug.security import generate_password_hash
from models import db, User

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username'].strip()
        password = request.form['password']
        role = request.form['role']
        school = request.form.get('school')
        student_number = request.form.get('student_number')
        classroom = request.form.get('classroom')
        teacher_code = request.form.get('teacher_code')
        admin_code = request.form.get('admin_code')

        errors = {}

        # ตรวจชื่อผู้ใช้ซ้ำ
        if User.query.filter_by(username=username).first():
            errors['error_username'] = "⚠️ ชื่อผู้ใช้นี้ถูกใช้แล้ว"
        elif len(username) < 4:
            errors['error_username'] = "⚠️ ต้องมีอย่างน้อย 4 ตัวอักษร"

        # ตรวจรหัสผ่าน
        if len(password) < 6:
            errors['error_password'] = "⚠️ ต้องมีอย่างน้อย 6 ตัวอักษร"

        
        if role == 'teacher':
            if teacher_code != 'TEACH123':  
                flash("❌ รหัสลับครูไม่ถูกต้อง", "error")
                return render_template("register.html",
                    name=name, username=username, role=role, school=school,
                    student_number=student_number, classroom=classroom,
                    teacher_code=teacher_code, admin_code=admin_code, **errors)

        if role == 'admin':
            if admin_code != 'ADMIN123':  
                flash("❌ รหัสลับแอดมินไม่ถูกต้อง", "error")
                return render_template("register.html",
                    name=name, username=username, role=role, school=school,
                    student_number=student_number, classroom=classroom,
                    teacher_code=teacher_code, admin_code=admin_code, **errors)

        # ถ้ามี error
        if errors:
            return render_template(
                "register.html",
                name=name,
                username=username,
                role=role,
                school=school,
                student_number=student_number,
                classroom=classroom,
                teacher_code=teacher_code,
                admin_code=admin_code,
                **errors
            )

        
        new_user = User(
            name=name,
            username=username,
            password=generate_password_hash(password),
            role=role,
            school=school,
            student_number=student_number,
            classroom=classroom,
            secret_code=teacher_code or admin_code
        )
        db.session.add(new_user)
        db.session.commit()

        flash("✅ สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ", "success")
        return redirect(url_for('auth.login'))


    return render_template("register.html")


# ------------------------- LOGIN -------------------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        user = User.query.filter_by(username=username).first()

        # ❌ ถ้าไม่มี user หรือรหัสผิด
        if not user or not user.check_password(password):
            flash('❌ Invalid username or password', 'error')
            return redirect(url_for('auth.login'))

        # ✅ เข้าสู่ระบบสำเร็จ
        login_user(user)
        session['user_id'] = user.id
        session['role'] = (user.role or "").lower().strip()
        session['username'] = user.username

        print(f"✅ LOGIN SUCCESS: {user.username} | ROLE: {session['role']}")

        # ✅ พาไปหน้าตาม role
        role = session['role']
        if role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'teacher':
            return redirect(url_for('teacher.teacher_ranking'))
        elif role == 'student':
            return redirect(url_for('student.dashboard_en'))
        else:
            flash("⚠️ Invalid role or missing route.")
            return redirect(url_for('auth.login'))

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('👋 Logged out successfully.')
    return redirect(url_for('auth.login'))
