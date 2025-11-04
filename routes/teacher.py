from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User, Game, GameScore, Lesson, QuizResult

teacher_bp = Blueprint("teacher", __name__, url_prefix="/teacher")

# ------------------------- RANKING -------------------------
@teacher_bp.route("/ranking")
@login_required
def teacher_ranking():
    if current_user.role != "teacher":
        flash("❌ เฉพาะครูเท่านั้นที่เข้าได้")
        return redirect(url_for("student.dashboard_en"))

    classroom = request.args.get("classroom")

    # Fetching all students in the same school
    students_query = User.query.filter_by(role="student", school=current_user.school)
    if classroom:
        students_query = students_query.filter_by(classroom=classroom)
    students = students_query.all()
    games = Game.query.all()

    # Calculating total score for each student
    ranking_data = []
    for student in students:
        total_score = 0
        for game in games:
            score_obj = GameScore.query.filter_by(user_id=student.id, game_id=game.id).first()
            total_score += score_obj.score if score_obj else 0
        ranking_data.append({"student": student, "total": total_score})

    # Sorting students by total score in descending order
    ranking = sorted(ranking_data, key=lambda x: x["total"], reverse=True)

    # Getting the classrooms for dropdown filter with count of students
    classrooms = (
        db.session.query(User.classroom, db.func.count(User.id))
        .filter(User.role == "student", User.school == current_user.school)
        .group_by(User.classroom)
        .all()
    )

    return render_template(
        "ranking.html",
        ranking=ranking,
        classrooms=classrooms,
        selected_classroom=classroom,
    )


# ------------------------- STUDENT REPORT -------------------------
@teacher_bp.route("/student/<int:student_id>/report")
@login_required
def student_report(student_id):
    if current_user.role != "teacher":
        flash("❌ เฉพาะครูเท่านั้นที่เข้าได้")
        return redirect(url_for("teacher.ranking"))

    student = User.query.get_or_404(student_id)

    # Game Scores
    game_scores = (
        db.session.query(GameScore, Game.title, Lesson.title)
        .join(Game, Game.id == GameScore.game_id)
        .join(Lesson, Lesson.id == Game.lesson_id)
        .filter(GameScore.user_id == student_id)
        .all()
    )

    # Quiz Scores
    quiz_scores = (
        db.session.query(QuizResult, Lesson.title)
        .join(Lesson, Lesson.id == QuizResult.lesson_id)
        .filter(QuizResult.user_id == student_id)
        .all()
    )

    total_game = sum([g.score for g, _, _ in game_scores]) if game_scores else 0
    total_quiz = sum([q.score for q, _ in quiz_scores]) if quiz_scores else 0
    total = total_game + total_quiz

    return render_template(
        "student_report.html",  # Ensure the correct path
        student=student,
        game_scores=game_scores,
        quiz_scores=quiz_scores,
        total=total,
    )

# ------------------------- ALLOW RETAKE GAME -------------------------
@teacher_bp.route("/allow_retake/game/<int:student_id>/<int:game_id>", methods=["POST"])
@login_required
def allow_retake_game(student_id, game_id):
    if current_user.role != "teacher":
        flash("❌ เฉพาะครูเท่านั้นที่ทำได้")
        return redirect(url_for("teacher.teacher_ranking"))

    student = User.query.get_or_404(student_id)
    game = Game.query.get_or_404(game_id)

    # ลบคะแนนเก่า (เพื่อให้เล่นใหม่)
    GameScore.query.filter_by(user_id=student_id, game_id=game_id).delete()
    db.session.commit()

    flash(f"✅ อนุมัติให้นักเรียน {student.name} เล่นเกม '{game.title}' ใหม่ได้แล้ว")
    return redirect(url_for("teacher.student_report", student_id=student_id))

# ------------------------- ALLOW RETAKE QUIZ -------------------------
@teacher_bp.route("/allow_retake/quiz/<int:student_id>/<int:lesson_id>/<string:test_type>", methods=["POST"])
@login_required
def allow_retake_quiz(student_id, lesson_id, test_type):
    if current_user.role != "teacher":
        flash("❌ เฉพาะครูเท่านั้นที่ทำได้")
        return redirect(url_for("teacher.ranking"))

    student = User.query.get_or_404(student_id)
    lesson = Lesson.query.get_or_404(lesson_id)

    QuizResult.query.filter_by(
        user_id=student_id, lesson_id=lesson_id, test_type=test_type
    ).delete()
    db.session.commit()

    flash(
        f"✅ อนุมัติให้นักเรียน {student.name} ทำแบบทดสอบ ({test_type.upper()}) ของ '{lesson.title}' ใหม่ได้แล้ว"
    )
    return redirect(url_for("teacher.student_report", student_id=student_id))

@teacher_bp.route("/reset_game_score/<int:student_id>/<int:game_id>", methods=["POST"])
@login_required
def reset_game_score(student_id, game_id):
    if current_user.role != "teacher":
        flash("❌ เฉพาะครูเท่านั้นที่ทำได้")
        return redirect(url_for("teacher.teacher_ranking"))

    student = User.query.get_or_404(student_id)
    game = Game.query.get_or_404(game_id)

    # ลบคะแนนเก่า (เพื่อให้เล่นใหม่)
    GameScore.query.filter_by(user_id=student_id, game_id=game_id).delete()
    db.session.commit()

    flash(f"✅ อนุมัติให้นักเรียน {student.name} เล่นเกม '{game.title}' ใหม่ได้แล้ว")
    return redirect(url_for("teacher.student_report", student_id=student_id))
@teacher_bp.route("/reset_quiz_score/<int:student_id>/<int:lesson_id>/<string:test_type>", methods=["POST"])
@login_required
def reset_quiz_score(student_id, lesson_id, test_type):
    if current_user.role != "teacher":
        flash("❌ เฉพาะครูเท่านั้นที่ทำได้")
        return redirect(url_for("teacher.teacher_ranking"))

    student = User.query.get_or_404(student_id)
    lesson = Lesson.query.get_or_404(lesson_id)

    # ลบคะแนนเก่า (เพื่อให้ทำใหม่)
    QuizResult.query.filter_by(user_id=student_id, lesson_id=lesson_id, test_type=test_type).delete()
    db.session.commit()

    flash(f"✅ อนุมัติให้นักเรียน {student.name} ทำแบบทดสอบ ({test_type.upper()}) ของ '{lesson.title}' ใหม่ได้แล้ว")
    return redirect(url_for("teacher.student_report", student_id=student_id))
