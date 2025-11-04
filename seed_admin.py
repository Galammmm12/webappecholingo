# seed_admin.py
from app import app, db, User
from werkzeug.security import generate_password_hash
from datetime import datetime

with app.app_context():
    # ลบ user admin เก่าออกก่อน (กันซ้ำ)
    old_admin = User.query.filter_by(username="admin").first()
    if old_admin:
        db.session.delete(old_admin)
        db.session.commit()

    # เพิ่ม admin ใหม่
    admin = User(
        username="admin",
        password=generate_password_hash("admin123"),  # ✅ เก็บเป็น hash
        role="admin",
        school=None,
        created_at=datetime.utcnow()
    )
    db.session.add(admin)
    db.session.commit()
    print("✅ สร้างแอดมินสำเร็จ username=admin, password=admin123")
