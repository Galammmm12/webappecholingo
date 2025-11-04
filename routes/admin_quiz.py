from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Lesson, Exercise, QuizResult
import os, uuid

admin_quiz_bp = Blueprint("admin_quiz", __name__, url_prefix="/admin/quiz")
quiz_bp = Blueprint("quiz", __name__, url_prefix="/quiz")

UPLOAD_FOLDER = "static/images"

@admin_quiz_bp.route("/lesson/<int:lesson_id>")
@login_required
def lesson_questions(lesson_id):
    if (current_user.role or "").lower() != "admin":
        flash("❌ เฉพาะผู้ดูแลระบบเท่านั้นที่เข้าหน้านี้ได้")
        return redirect(url_for("admin.dashboard"))

    lesson = Lesson.query.get_or_404(lesson_id)
    questions = Exercise.query.filter(
        Exercise.lesson_id == lesson_id,
        Exercise.question_type.in_(["pre", "post", "pre_zh", "post_zh"])
    ).all()

    return render_template("lesson_questions.html", lesson=lesson, questions=questions)

@admin_quiz_bp.route("/add/<int:lesson_id>", methods=["GET", "POST"])
@login_required
def add_question(lesson_id):
    if (current_user.role or "").lower() != "admin":
        flash("❌ เฉพาะผู้ดูแลระบบเท่านั้นที่เพิ่มคำถามได้")
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
        question_type=request.form.get("question_type", "pre"),
        question=request.form.get("question", ""),
        option_a=request.form.get("option_a", ""),
        option_b=request.form.get("option_b", ""),
        option_c=request.form.get("option_c", ""),
        option_d=request.form.get("option_d", ""),
        correct_option=request.form.get("correct_option", "A").strip().upper(),
        image_path=image_path,
        lang=request.form.get("lang", lesson.lang or "en")  
)

        db.session.add(new_q)
        db.session.commit()
        flash("✅ เพิ่มคำถามใหม่เรียบร้อยแล้ว")
        return redirect(url_for("admin_quiz.lesson_questions", lesson_id=lesson.id))

    return render_template("add_question.html", lesson=lesson)

@admin_quiz_bp.route("/edit/<int:question_id>", methods=["GET", "POST"])
@login_required
def edit_question(question_id):
    if (current_user.role or "").lower() != "admin":
        flash("❌ เฉพาะแอดมินเท่านั้นที่แก้ไขได้")
        return redirect(url_for("admin.dashboard"))

    q = Exercise.query.get_or_404(question_id)
    lesson = Lesson.query.get_or_404(q.lesson_id)

    if request.method == "POST":
        q.question_type = request.form.get("question_type", q.question_type)
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



# ✅ ฟังก์ชัน core สำหรับทำแบบทดสอบ (รวมทุก test_type)
def _take_quiz_core(lesson_id, lang, test_type):
    lesson = Lesson.query.get_or_404(lesson_id)
    lang = (lang or "").lower()

    questions = Exercise.query.filter(
        Exercise.lesson_id == lesson_id,
        Exercise.question_type.in_([test_type, f"{test_type}_zh"]),
        Exercise.lang.ilike(f"%{lang[:2]}%")
    ).all()

    # ไม่มีคำถาม
    if not questions:
        flash("❌ ยังไม่มีคำถามสำหรับแบบทดสอบนี้")
        return render_template("quiz_error.html", lesson=lesson, questions=[], test_type=test_type, lang=lang)

    # ตรวจว่าทำแล้วหรือยัง
    done = QuizResult.query.filter_by(
        user_id=current_user.id,
        lesson_id=lesson_id,
        test_type=test_type
    ).first()
    if done:
        flash("คุณได้ทำแบบทดสอบนี้แล้ว ✅")
        return redirect(url_for("student.dashboard_en"))

    # เมื่อกดส่ง
    if request.method == "POST":
        score = 0
        results = []

        for q in questions:
            user_answer = request.form.get(f"q{q.id}")
            correct = user_answer and user_answer.upper() == q.correct_option.upper()
            if correct:
                score += 1
            results.append({
                "question": q.question,
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d,
                "correct_option": q.correct_option,
                "user_answer": user_answer,
                "image_path": q.image_path
            })

        db.session.add(QuizResult(
            user_id=current_user.id,
            lesson_id=lesson.id,
            test_type=test_type,
            score=score
        ))
        db.session.commit()

        return render_template(
            "quiz_result.html",
            test_type=test_type,
            score=score,
            total=len(questions),
            results=results,
            lesson=lesson,
            lang=lang
        )

    # 🧠 ถ้ายังไม่ได้กดส่ง — แสดงหน้าทำแบบทดสอบ
    return render_template("quiz_zh.html", lesson=lesson, questions=questions, test_type=test_type, lang=lang)

@admin_quiz_bp.route("/take/<int:lesson_id>/<lang>/<test_type>", methods=["GET", "POST"])
@login_required
def take_quiz(lesson_id, lang, test_type):
    if (current_user.role or "").lower() not in ["admin", "teacher"]:
        flash("❌ เฉพาะผู้ดูแลระบบหรือครูเท่านั้นที่เข้าได้")
        return redirect(url_for("student.dashboard_en"))
    return _take_quiz_core(lesson_id, lang, test_type)
 
@quiz_bp.route("/take/<int:lesson_id>/<lang>/<test_type>", methods=["GET", "POST"])
@login_required
def student_take_quiz(lesson_id, lang, test_type):   # ✅ เปลี่ยนชื่อกลับให้ถูก
    return _take_quiz_core(lesson_id, lang, test_type)   # ✅ เรียกใช้ฟังก์ชันหลักที่อยู่ด้านบน


# ✅ เพิ่ม fallback ป้องกัน None response
def quiz_fallback(lesson_id, lang, test_type):
    return render_template(
        "quiz_error.html",
        message="⚠️ ไม่สามารถเริ่มแบบทดสอบได้ หรือไม่พบคำถาม",
        lesson_id=lesson_id,
        lang=lang,
        test_type=test_type
    )
