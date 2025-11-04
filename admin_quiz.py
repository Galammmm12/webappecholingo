# ============================================================
# 📦 routes/admin_quiz.py — ระบบจัดการ Quiz (แอดมิน)
# ============================================================
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Lesson, Exercise
import os, uuid

admin_quiz_bp = Blueprint("admin_quiz", __name__, url_prefix="/admin/quiz")
UPLOAD_FOLDER = "static/images"

# ============================================================
# 📋 แสดงคำถามทั้งหมดในบทเรียน
# ============================================================
@admin_quiz_bp.route("/lesson/<int:lesson_id>")
@login_required
def lesson_questions(lesson_id):
    if (current_user.role or "").lower() != "admin":
        flash("❌ เฉพาะผู้ดูแลระบบเท่านั้นที่เข้าหน้านี้ได้")
        return redirect(url_for("admin.dashboard"))

    lesson = Lesson.query.get_or_404(lesson_id)
    questions = Exercise.query.filter_by(lesson_id=lesson_id, question_type="game").all()
    return render_template("lesson_questions.html", lesson=lesson, questions=questions)

# ============================================================
# ➕ เพิ่มคำถามใหม่
# ============================================================
@admin_quiz_bp.route("/add/<int:lesson_id>", methods=["GET", "POST"])
@login_required
def add_question(lesson_id):
    if (current_user.role or "").lower() != "admin":
        flash("❌ เฉพาะแอดมินเท่านั้นที่เพิ่มคำถามได้")
        return redirect(url_for("admin.dashboard"))

    lesson = Lesson.query.get_or_404(lesson_id)

    if request.method == "POST":
        image_file = request.files.get("image")
        image_path = None
        if image_file and image_file.filename:
            ext = os.path.splitext(image_file.filename)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            image_file.save(os.path.join(UPLOAD_FOLDER, filename))
            image_path = f"images/{filename}"

        new_q = Exercise(
            lesson_id=lesson.id,
            question_type="game",
            question=request.form["question"],
            option_a=request.form["option_a"],
            option_b=request.form["option_b"],
            option_c=request.form["option_c"],
            option_d=request.form["option_d"],
            correct_option=request.form["correct_option"].strip().upper(),
            image_path=image_path,
            lang=lesson.lang
        )
        db.session.add(new_q)
        db.session.commit()
        flash("✅ เพิ่มคำถามใหม่เรียบร้อยแล้ว")
        return redirect(url_for("admin_quiz.lesson_questions", lesson_id=lesson.id))

    return render_template("add_question.html", lesson=lesson)

# ============================================================
# ✏️ แก้ไขคำถาม
# ============================================================
@admin_quiz_bp.route("/edit/<int:question_id>", methods=["GET", "POST"])
@login_required
def edit_question(question_id):
    if (current_user.role or "").lower() != "admin":
        flash("❌ เฉพาะแอดมินเท่านั้นที่แก้ไขได้")
        return redirect(url_for("admin.dashboard"))

    q = Exercise.query.get_or_404(question_id)
    lesson = Lesson.query.get_or_404(q.lesson_id)

    if request.method == "POST":
        q.question = request.form["question"]
        q.option_a = request.form["option_a"]
        q.option_b = request.form["option_b"]
        q.option_c = request.form["option_c"]
        q.option_d = request.form["option_d"]
        q.correct_option = request.form["correct_option"].strip().upper()

        image_file = request.files.get("image")
        if image_file and image_file.filename:
            ext = os.path.splitext(image_file.filename)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            image_file.save(os.path.join(UPLOAD_FOLDER, filename))
            q.image_path = f"images/{filename}"

        db.session.commit()
        flash("✅ บันทึกการแก้ไขเรียบร้อยแล้ว")
        return redirect(url_for("admin_quiz.lesson_questions", lesson_id=q.lesson_id))

    return render_template("edit_question.html", question=q, lesson=lesson)

# ============================================================
# 🗑️ ลบคำถาม
# ============================================================
@admin_quiz_bp.route("/delete/<int:question_id>", methods=["POST"])
@login_required
def delete_question(question_id):
    if (current_user.role or "").lower() != "admin":
        flash("❌ เฉพาะแอดมินเท่านั้นที่ลบได้")
        return redirect(url_for("admin.dashboard"))

    q = Exercise.query.get_or_404(question_id)
    lesson_id = q.lesson_id
    db.session.delete(q)
    db.session.commit()
    flash("🗑️ ลบคำถามเรียบร้อยแล้ว")
    return redirect(url_for("admin_quiz.lesson_questions", lesson_id=lesson_id))
