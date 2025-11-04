from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from models import (
    db, Lesson, Game, GameScore, QuizResult,
    Exercise, FillInBlank, MatchingItem, ScrambleItem, SpeechQuestion,ChoiceItem
)

student_bp = Blueprint("student", __name__, url_prefix="/student")

@student_bp.route("/dashboard_en")
@login_required
def dashboard_en():
    lessons = Lesson.query.filter_by(lang="en").all()
    return render_template("student_dashboard.html", lessons=lessons, lang="en")

# 🏠 Dashboard (ZH)
@student_bp.route("/dashboard_zh")
@login_required
def dashboard_zh():
    lessons = Lesson.query.filter_by(lang="zh").all()
    return render_template("student_dashboard_zh.html", lessons=lessons, lang="zh")

# 🧩 Exercise Score (EN)
@student_bp.route("/exercise_score_en")
@login_required
def exercise_score_en():
    lessons = Lesson.query.filter_by(lang="en").all()
    lesson_scores = []
    for lesson in lessons:
        score = (
            db.session.query(db.func.max(GameScore.score))
            .join(Game, Game.id == GameScore.game_id)
            .filter(Game.lesson_id == lesson.id, GameScore.user_id == current_user.id)
            .scalar()
        ) or 0
        lesson_scores.append({"lesson": lesson, "score": score})
    return render_template("student_score.html", lessons=lesson_scores, lang="en")

# 🧩 Exercise Score (ZH)
@student_bp.route("/exercise_score_zh")
@login_required
def exercise_score_zh():
    lessons = Lesson.query.filter_by(lang="zh").all()
    lesson_scores = []
    for lesson in lessons:
        score = (
            db.session.query(db.func.max(GameScore.score))
            .join(Game, Game.id == GameScore.game_id)
            .filter(Game.lesson_id == lesson.id, GameScore.user_id == current_user.id)
            .scalar()
        ) or 0
        lesson_scores.append({"lesson": lesson, "score": score})
    return render_template("exercise_score_zh.html", lessons=lesson_scores, lang="zh")

# 🧪 Test Scores (EN)
@student_bp.route("/test_scores_en")
@login_required
def test_scores_en():
    lessons = Lesson.query.filter_by(lang="en").all()
    data = []
    for lesson in lessons:
        pre = QuizResult.query.filter_by(user_id=current_user.id, lesson_id=lesson.id, test_type="pre").first()
        post = QuizResult.query.filter_by(user_id=current_user.id, lesson_id=lesson.id, test_type="post").first()
        data.append({
            "lesson": lesson,
            "pre_score": pre.score if pre else None,
            "post_score": post.score if post else None
        })
    return render_template("test_scores.html", lesson_scores=data, lang="en")

# 🧪 Test Scores (ZH)
@student_bp.route("/test_scores_zh")
@login_required
def test_scores_zh():
    lessons = Lesson.query.filter_by(lang="zh").all()
    data = []
    for lesson in lessons:
        pre = QuizResult.query.filter_by(user_id=current_user.id, lesson_id=lesson.id, test_type="pre").first()
        post = QuizResult.query.filter_by(user_id=current_user.id, lesson_id=lesson.id, test_type="post").first()
        data.append({
            "lesson": lesson,
            "pre_score": pre.score if pre else None,
            "post_score": post.score if post else None
        })
    return render_template("test_scores_zh.html", lesson_scores=data, lang="zh")

# 🎯 Unit Detail
@student_bp.route("/unit/<int:unit_id>")
@login_required
def unit_detail(unit_id):
    unit = Lesson.query.get_or_404(unit_id)
    games = Game.query.filter_by(lesson_id=unit_id).all()

    # เช็กเกมที่เคยเล่น
    for g in games:
        g.played = GameScore.query.filter_by(user_id=current_user.id, game_id=g.id).first() is not None

    # เช็ก pre/post
    pre_done = QuizResult.query.filter_by(user_id=current_user.id, lesson_id=unit_id, test_type="pre").first() is not None
    post_done = QuizResult.query.filter_by(user_id=current_user.id, lesson_id=unit_id, test_type="post").first() is not None

    template = "unit_detail.html" if unit.lang == "en" else "unit_detail_zh.html"
    return render_template(template, unit=unit, games=games, pre_done=pre_done, post_done=post_done, lang=unit.lang)

# 🏆 Lesson Score Detail (EN)
@student_bp.route('/student/score/lesson/<int:lesson_id>')
def lesson_score_detail(lesson_id):
    if 'user_id' not in session or session.get('role') != 'student':
        flash('❌ กรุณาล็อกอินก่อน')
        return redirect(url_for('login'))

    user_id = session['user_id']
    lesson = Lesson.query.get_or_404(lesson_id)
    games = Game.query.filter_by(lesson_id=lesson.id).order_by(Game.id).all()

    scores = []
    for g in games:
        latest = (
            GameScore.query
            .filter_by(user_id=user_id, game_id=g.id)
            .order_by(GameScore.played_at.desc())
            .first()
        )
        score_val = latest.score if latest else 0

        # ✅ ดึงจำนวนข้อของเกมนั้น
        if g.game_type in ["quiz", "exam", "test"]:
            max_q = Exercise.query.filter_by(lesson_id=g.lesson_id, question_type="game", lang=g.lang).count()
        elif g.game_type in ["choice", "choice_match"]:
            max_q = ChoiceItem.query.filter_by(game_id=g.id).count()
        elif g.game_type in ["scramble"]:
            max_q = ScrambleItem.query.filter_by(game_id=g.id).count()
        elif g.game_type in ["fill", "fill-in-the-blank"]:
            max_q = FillInBlank.query.filter_by(game_id=g.id).count()
        elif g.game_type in ["matching"]:
            max_q = MatchingItem.query.filter_by(game_id=g.id).count()
        else:
            max_q = 10  # fallback

        scores.append({"score": score_val, "max": max_q})

    return render_template(
        "lesson_score_detail.html",
        lesson=lesson,
        games=games,
        scores=scores,
        username=session.get('username', 'Student')
    )

# 🏆 Lesson Score Detail (ZH)
@student_bp.route('/student/score/lesson/<int:lesson_id>/zh')
def lesson_score_detail_zh(lesson_id):
    if 'user_id' not in session or session.get('role') != 'student':
        flash('❌ 请先登录')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # ดึงบทเรียน (จีน)
    lesson = Lesson.query.get_or_404(lesson_id)

    # ดึงเกมในบทนี้ทั้งหมด
    games = Game.query.filter_by(lesson_id=lesson.id).order_by(Game.id).all()

    scores = []
    for g in games:
        latest = (
            GameScore.query
            .filter_by(user_id=user_id, game_id=g.id)
            .order_by(GameScore.played_at.desc())
            .first()
        )
        score_val = latest.score if latest else 0
        scores.append(score_val)

    # 🔎 Debug print
    print("DEBUG >> Lesson ZH:", lesson.title)
    print("DEBUG >> Games ZH:", [g.title for g in games])
    print("DEBUG >> Scores ZH:", scores)

    return render_template(
        "lesson_score_detail_zh.html", 
        lesson=lesson,
        games=games,
        scores=scores,
        username=session.get('username', '学生')
    )

