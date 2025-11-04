from flask import Blueprint, render_template, flash, redirect, url_for, request, session
from flask_login import login_required, current_user
from models import (
    db, Lesson, Exercise, Game, GameType,
    GameItem, QuizItem, ChoiceItem, MatchingItem,
    ScrambleItem, FillInBlank, SpeechQuestion
)
from werkzeug.utils import secure_filename
import os

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
def admin_only():
    if (current_user.role or "").lower() != "admin":
        flash("❌ เฉพาะผู้ดูแลระบบเท่านั้นที่เข้าหน้านี้ได้", "danger")
        return False
    return True

@admin_bp.route("/dashboard")
@login_required
def dashboard():
    if not admin_only():
        return redirect("/")
    
    lessons = Lesson.query.all()
    games = Game.query.all()
    exercises = Exercise.query.all()
    game_types = GameType.query.all()

    return render_template(
        "admin_dashboard.html",
        lessons=lessons,
        games=games,
        exercises=exercises,
        game_types=game_types
    )
@admin_bp.route("/lessons")
@login_required
def manage_lessons():
    if not admin_only():
        return redirect("/")
    lessons = Lesson.query.all()
    return render_template("admin_lessons.html", lessons=lessons)

@admin_bp.route("/lesson/add", methods=["GET", "POST"])
@login_required
def add_lesson():
    if not admin_only():
        return redirect("/")
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        lang = request.form["lang"]
        new_lesson = Lesson(title=title, description=description, lang=lang)
        db.session.add(new_lesson)
        db.session.commit()
        flash("✅ เพิ่มบทเรียนเรียบร้อย", "success")
        return redirect(url_for("admin.manage_lessons"))
    return render_template("admin_add_lesson.html")

@admin_bp.route("/lesson/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_lesson(id):

    if not admin_only():
        return redirect("/")
    lesson = Lesson.query.get_or_404(id)

    if request.method == "POST":
        lesson.title = request.form["title"]
        lesson.lang = request.form["language"]
        lesson.description = request.form.get("description", "")
        db.session.commit()
        flash("✏️ แก้ไขบทเรียนเรียบร้อย", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin_lesson_edit.html", lesson=lesson)


@admin_bp.route("/lesson/delete/<int:lesson_id>", methods=["POST"])
@login_required
def delete_lesson(lesson_id):

    if not admin_only():
        return redirect("/")
    lesson = Lesson.query.get_or_404(lesson_id)
    db.session.delete(lesson)
    db.session.commit()
    flash("🗑️ ลบบทเรียนเรียบร้อย", "success")
    return redirect(url_for("admin.manage_lessons"))

@admin_bp.route("/games")
@login_required
def manage_games():
    if not admin_only():
        return redirect("/")
    games = Game.query.all()
    return render_template("admin_games.html", games=games)


@admin_bp.route("/game/add", methods=["GET", "POST"])
@login_required
def add_game():
    if not admin_only():
        return redirect("/")
    lessons = Lesson.query.all()
    game_types = GameType.query.all()

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        game_type = request.form["game_type"].strip().lower()
        lesson_id = request.form["lesson_id"]
        lang = request.form["lang"] or "en"

        # ✅ บังคับให้ "เกมพูด" ใช้ชื่อ game_type = 'speech'
        if game_type in ["speaking", "พูด", "พูดคุย", "speaking game"]:
            game_type = "speech"

        new_game = Game(
            title=title,
            description=description,
            game_type=game_type,
            lesson_id=lesson_id,
            lang=lang
        )
        db.session.add(new_game)
        db.session.commit()
        flash("✅ เพิ่มเกมสำเร็จ", "success")

        return redirect(url_for("admin.lesson_games", lesson_id=lesson_id))

    return render_template("admin_game_add.html", lessons=lessons, game_types=game_types)


@admin_bp.route('/game/<int:game_id>/edit', methods=['GET', 'POST'])
def edit_game(game_id):
    game = Game.query.get_or_404(game_id)
    if request.method == 'POST':
        game.title = request.form['title']
        game.description = request.form.get('description')
        game.game_type = request.form['game_type']
        game.lesson_id = int(request.form['lesson_id'])
        game.title_pinyin = request.form.get('title_pinyin')
        game.description_pinyin = request.form.get('description_pinyin')
        db.session.commit()
        flash('✅ แก้ไขข้อมูลเกมเรียบร้อยแล้ว')
        return redirect(url_for('admin.view_game_detail', game_id=game_id))
    return render_template('edit_game.html',
                           game=game,
                           lessons=Lesson.query.filter_by(lang=game.lang).all(),
                           game_types=GameType.query.all())


@admin_bp.route("/game/delete/<int:game_id>", methods=["POST"])
@login_required
def delete_game(game_id):
    if not admin_only():
        return redirect("/")
    game = Game.query.get_or_404(game_id)
    lesson_id = game.lesson_id  # ✅ จำบทก่อนลบ
    db.session.delete(game)
    db.session.commit()
    flash("🗑️ ลบเกมเรียบร้อย", "success")

    # ✅ กลับไปหน้าเกมของบทเรียนเดิม
    return redirect(url_for("admin.lesson_games", lesson_id=lesson_id))

# ------------------------------------------------------------
# 📖 จัดการแบบฝึกหัด (Exercise Management)
# ------------------------------------------------------------
@admin_bp.route("/exercises")
@login_required
def manage_exercises():
    if not admin_only():
        return redirect("/")
    exercises = Exercise.query.all()
    return render_template("admin_exercises.html", exercises=exercises)


@admin_bp.route("/exercise/add", methods=["GET", "POST"])
@login_required
def add_exercise():
    if not admin_only():
        return redirect("/")
    lessons = Lesson.query.all()
    if request.method == "POST":
        question = request.form["question"]
        correct_option = request.form["correct_option"]
        lesson_id = request.form["lesson_id"]
        question_type = request.form["question_type"]
        lang = request.form["lang"]

        new_ex = Exercise(
            question=question,
            correct_option=correct_option,
            lesson_id=lesson_id,
            question_type=question_type,
            lang=lang
        )
        db.session.add(new_ex)
        db.session.commit()
        flash("✅ เพิ่มแบบฝึกหัดสำเร็จ", "success")
        return redirect(url_for("admin.manage_exercises"))
    return render_template("admin_add_exercise.html", lessons=lessons)


@admin_bp.route("/exercise/edit/<int:exercise_id>", methods=["GET", "POST"])
@login_required
def edit_exercise(exercise_id):
    if not admin_only():
        return redirect("/")
    exercise = Exercise.query.get_or_404(exercise_id)
    lessons = Lesson.query.all()
    if request.method == "POST":
        exercise.question = request.form["question"]
        exercise.correct_option = request.form["correct_option"]
        exercise.lesson_id = request.form["lesson_id"]
        exercise.question_type = request.form["question_type"]
        exercise.lang = request.form["lang"]
        db.session.commit()
        flash("✏️ แก้ไขแบบฝึกหัดเรียบร้อย", "success")
        return redirect(url_for("admin.manage_exercises"))
    return render_template("admin_edit_exercise.html", exercise=exercise, lessons=lessons)


@admin_bp.route("/exercise/delete/<int:exercise_id>")
@login_required
def delete_exercise(exercise_id):
    if not admin_only():
        return redirect("/")
    exercise = Exercise.query.get_or_404(exercise_id)
    db.session.delete(exercise)
    db.session.commit()
    flash("🗑️ ลบแบบฝึกหัดเรียบร้อย", "success")
    return redirect(url_for("admin.manage_exercises"))
# ------------------------------------------------------------
# 🎮 แสดงรายชื่อเกมของบทเรียน (สำหรับแอดมิน)
# ------------------------------------------------------------
@admin_bp.route("/lesson/<int:lesson_id>/games")
@login_required
def lesson_games(lesson_id):
    if (current_user.role or "").lower() != "admin":
        flash("❌ เฉพาะผู้ดูแลระบบเท่านั้นที่เข้าหน้านี้ได้")
        return redirect(url_for("admin.dashboard"))
    
    from models import Lesson, Game  # import ซ้ำได้ ปลอดภัย
    lesson = Lesson.query.get_or_404(lesson_id)
    games = Game.query.filter_by(lesson_id=lesson_id).all()

    return render_template("lesson_games.html", lesson=lesson, games=games)

# ---------------------------------------------------
# 📄 หน้าแสดง Pre-Test / Post-Test ของบทเรียน
# ---------------------------------------------------
@admin_bp.route('/lesson/<int:lesson_id>/tests')
@login_required
def lesson_tests(lesson_id):
    # ดึงข้อมูลบทเรียน
    lesson = Lesson.query.get_or_404(lesson_id)

    # ดึงคำถามทั้งหมดที่เกี่ยวข้องกับบทเรียนนี้
    test_questions = Exercise.query.filter_by(lesson_id=lesson_id).all()

    return render_template(
        'lesson_tests.html',
        lesson=lesson,
        test_questions=test_questions
    )
# ------------------------------------------------------------
# 🗂️ จัดการประเภทเกม (GameType Management)
# ------------------------------------------------------------
@admin_bp.route("/gametype/add", methods=["GET", "POST"])
@login_required
def add_gametype():
    if not admin_only():
        return redirect("/")
    if request.method == "POST":
        name = request.form["name"]
        description = request.form.get("description", "")
        new_type = GameType(name=name, description=description)
        db.session.add(new_type)
        db.session.commit()
        flash("✅ เพิ่มประเภทเกมสำเร็จ", "success")
        return redirect(url_for("admin.dashboard"))
    return render_template("admin_add_gametype.html")


@admin_bp.route("/gametype/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_gametype(id):
    if not admin_only():
        return redirect("/")
    game_type = GameType.query.get_or_404(id)
    if request.method == "POST":
        game_type.name = request.form["name"]
        game_type.description = request.form.get("description", "")
        db.session.commit()
        flash("✏️ แก้ไขประเภทเกมเรียบร้อย", "success")
        return redirect(url_for("admin.dashboard"))
    return render_template("admin_edit_gametype.html", game_type=game_type)


@admin_bp.route("/gametype/delete/<int:id>", methods=["POST"])
@login_required
def delete_gametype(id):
    if not admin_only():
        return redirect("/")
    game_type = GameType.query.get_or_404(id)
    db.session.delete(game_type)
    db.session.commit()
    flash("🗑️ ลบประเภทเกมเรียบร้อย", "success")
    return redirect(url_for("admin.dashboard"))

@admin_bp.route('/game/<int:game_id>/detail')
@login_required
def view_game_detail(game_id):
    if not admin_only():
        return redirect("/")
        
    game = Game.query.get_or_404(game_id)
    gtype = (game.game_type or "").strip().lower()

    if gtype in ["drag", "drag drop"]:
        items = GameItem.query.filter_by(game_id=game_id).all()
        return render_template("game_detail_drag.html", game=game, items=items)

    elif gtype in ["fill", "fill-in-the-blank", "fill in the blank", "เติมคำ"]:
        items = FillInBlank.query.filter_by(game_id=game_id).all()
        return render_template("game_detail_fill.html", game=game, items=items)

    elif gtype in ["matching", "match", "จับคู่"]:
        items = MatchingItem.query.filter_by(game_id=game_id).all()
        return render_template("game_detail_matching.html", game=game, items=items)

    elif gtype in ["scramble", "sentence scramble", "เรียงคำ"]:
        items = ScrambleItem.query.filter_by(game_id=game_id).all()
        return render_template("game_detail_scramble.html", game=game, items=items)

    elif gtype in ["choice_match", "choice"]:
        items = ChoiceItem.query.filter_by(game_id=game_id).all()
        return render_template("game_detail_choice.html", game=game, items=items)

    elif gtype in ["quiz", "quiz_game"]:
        items = Exercise.query.filter_by(
            lesson_id=game.lesson_id,
            question_type="game",
            lang=game.lang
        ).all()
        return render_template("game_detail_quiz.html", game=game, items=items)

    elif gtype in ["speaking", "speech", "พูด"]:
        items = SpeechQuestion.query.filter_by(game_id=game_id).all()
        return render_template("game_detail_speech.html", game=game, items=items)

    flash(f"❌ ไม่รู้จักประเภทเกมนี้: {game.game_type}")
    return redirect(url_for("admin.dashboard"))

# ------------------------------------------------------------
# 🧩 เพิ่ม / ลบ / แก้ไข ข้อในเกมประเภท Matching
# ------------------------------------------------------------
from werkzeug.utils import secure_filename
import os

@admin_bp.route("/game/<int:game_id>/add_matching_item", methods=["GET", "POST"])
@login_required
def add_matching_item(game_id):
    if not admin_only():
        return redirect("/")

    game = Game.query.get_or_404(game_id)

    if request.method == "POST":
        audio_file = request.files.get("question_audio")
        answer_text = request.form.get("answer_text")
        pair_group = request.form.get("pair_group")

        audio_path = None

        # ✅ ตรวจสอบการอัปโหลดไฟล์เสียง
        if audio_file and audio_file.filename != "":
            filename = secure_filename(audio_file.filename)

            # ✅ ตั้งชื่อไฟล์ไม่ให้ซ้ำ เช่น matching_41_20251022_123456.mp3
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = filename.rsplit(".", 1)[-1]
            new_filename = f"matching_{game_id}_{timestamp}.{ext}"

            upload_folder = os.path.join("static", "uploads")
            os.makedirs(upload_folder, exist_ok=True)
            audio_file.save(os.path.join(upload_folder, new_filename))

            # ✅ เก็บพาธสำหรับใช้ url_for('admin.serve_upload')
            audio_path = f"uploads/{new_filename}"

        # ✅ ตรวจสอบข้อมูล
        if not answer_text or not pair_group:
            flash("⚠️ กรุณากรอกข้อมูลให้ครบ", "warning")
            return redirect(request.url)

        new_item = MatchingItem(
            game_id=game.id,
            lesson_id=game.lesson_id,
            answer_text=answer_text,
            question_audio=audio_path,  # ✅ เสียงใหม่จากเครื่อง
            pair_group=pair_group
        )

        db.session.add(new_item)
        db.session.commit()
        flash("✅ เพิ่มข้อจับคู่พร้อมเสียงเรียบร้อย", "success")
        return redirect(url_for("admin.view_game_detail", game_id=game.id))

    return render_template("add_matching_item.html", game=game)


# ------------------------------------------------------------
# ✏️ แก้ไขข้อจับคู่ (Matching Item)
# ------------------------------------------------------------
@admin_bp.route("/game/<int:game_id>/edit_matching_item/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_matching_item(game_id, item_id):
    if not admin_only():
        return redirect("/")

    game = Game.query.get_or_404(game_id)
    item = MatchingItem.query.get_or_404(item_id)

    if request.method == "POST":
        answer_text = request.form.get("answer_text")
        pair_group = request.form.get("pair_group")

        # ✅ ถ้ามีการอัปโหลดไฟล์ใหม่
        audio_file = request.files.get("question_audio")
        if audio_file and audio_file.filename:
            from werkzeug.utils import secure_filename
            filename = secure_filename(audio_file.filename)
            upload_folder = os.path.join("static", "uploads")
            os.makedirs(upload_folder, exist_ok=True)
            audio_file.save(os.path.join(upload_folder, filename))
            item.question_audio = f"uploads/{filename}"

        # ✅ อัปเดตข้อมูลอื่น
        item.answer_text = answer_text
        item.pair_group = pair_group

        db.session.commit()
        flash("✅ แก้ไขคำถามจับคู่เรียบร้อยแล้ว", "success")
        return redirect(url_for("admin.view_game_detail", game_id=game_id))

    return render_template("edit_matching_item.html", game=game, item=item)

# ------------------------------------------------------------
# 🗑️ ลบข้อจับคู่ (Matching Item)
# ------------------------------------------------------------
@admin_bp.route("/game/<int:game_id>/delete_matching_item/<int:item_id>", methods=["POST"])
@login_required
def delete_matching_item(game_id, item_id):
    if not admin_only():
        return redirect("/")

    item = MatchingItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()

    flash("🗑️ ลบข้อจับคู่เรียบร้อยแล้ว", "success")
    return redirect(url_for("game_detail_matching.html", game_id=game_id))
# ------------------------------------------------------------
# 🧩 เพิ่ม / ลบ / แก้ไข ข้อในเกมประเภท Drag & Drop
# ------------------------------------------------------------
@admin_bp.route("/game/<int:game_id>/add_game_item", methods=["GET", "POST"])
@login_required
def add_game_item(game_id):
    if not admin_only():
        return redirect("/")

    game = Game.query.get_or_404(game_id)

    if request.method == "POST":
        # ดึงค่าจากฟอร์มอย่างปลอดภัย
        word = request.form.get("word") or request.form.get("correct_word")
        pinyin = request.form.get("pinyin")
        image_name = request.form.get("image_name")

        if not word:
            flash("⚠️ กรุณากรอกคำศัพท์ (word) ก่อนบันทึก", "warning")
            return redirect(request.url)

        new_item = GameItem(
            game_id=game_id,
            correct_word=word,
            pinyin=pinyin,
            image_name=image_name
        )
        db.session.add(new_item)
        db.session.commit()
        flash("✅ เพิ่มคำศัพท์ใหม่เรียบร้อย", "success")
        return redirect(url_for("admin.view_game_detail", game_id=game_id))

    return render_template("add_game_item.html", game=game)



@admin_bp.route("/game/<int:game_id>/edit_game_item/<int:item_id>", methods=["POST"])
@login_required
def edit_game_item(game_id, item_id):
    if not admin_only():
        return redirect("/")

    item = GameItem.query.get_or_404(item_id)
    item.word = request.form.get("word", item.word)
    item.translation = request.form.get("translation", item.translation)
    db.session.commit()

    flash("✏️ แก้ไขคำศัพท์เรียบร้อย", "success")
    return redirect(url_for('admin.view_game_detail', game_id=game_id))



@admin_bp.route("/game/<int:game_id>/delete_game_item/<int:item_id>", methods=["POST"])
@login_required
def delete_game_item(game_id, item_id):
    if not admin_only():
        return redirect("/")

    item = GameItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()

    flash("🗑️ ลบคำศัพท์เรียบร้อย", "success")
    return redirect(url_for("game_detail_drag.html", game_id=game_id))


@admin_bp.route("/game/<int:game_id>/add_speech_question", methods=["GET", "POST"])
@login_required
def add_speech_question(game_id):
    if not admin_only():
        return redirect("/")

    game = Game.query.get_or_404(game_id)

    if request.method == "POST":
        question_text = request.form["question_text"]
        correct_answer = request.form.get("correct_answer", "")
        pinyin = request.form.get("pinyin", "")
        lang = request.form.get("lang", "zh")

        # ✅ เพิ่ม lesson_id ให้สัมพันธ์กับเกม
        new_question = SpeechQuestion(
            game_id=game_id,
            
            question_text=question_text,
            correct_answer=correct_answer,
            pinyin=pinyin,
            lang=lang
        )
        db.session.add(new_question)
        db.session.commit()
        flash("✅ เพิ่มคำถามพูดเรียบร้อย", "success")
        return redirect(url_for("admin.view_game_detail", game_id=game.id))

    return render_template("add_speech_question.html", game=game)


@admin_bp.route("/game/<int:game_id>/edit_speech_question/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_speech_question(game_id, item_id):
    if not admin_only():
        return redirect("/")

    game = Game.query.get_or_404(game_id)
    question = SpeechQuestion.query.get_or_404(item_id)

    if request.method == "POST":
        question.question_text = request.form["question_text"]
        question.correct_answer = request.form["correct_answer"]  # ✅ ตรงกับ template
        question.pinyin = request.form.get("pinyin")
        question.lang = request.form.get("lang", "en")
        db.session.commit()
        flash("✏️ แก้ไขคำถามพูดเรียบร้อยแล้ว", "success")
        return redirect(url_for("admin.view_game_detail", game_id=game_id))

    return render_template("edit_speech_question.html", game=game, question=question)



# ------------------------------------------------------------
# 🗑️ ลบคำถามพูด (Speech Question)
# ------------------------------------------------------------
@admin_bp.route("/game/<int:game_id>/delete_speech_question/<int:item_id>", methods=["POST"])
@login_required
def delete_speech_question(game_id, item_id):
    
    if not admin_only():
        return redirect("/")

    question = SpeechQuestion.query.get_or_404(item_id)
    db.session.delete(question)
    db.session.commit()
    flash("🗑️ ลบคำถามพูดเรียบร้อยแล้ว", "success")
    return redirect(url_for("admin.view_game_detail", game_id=game_id))  # ✅ แก้ตรงนี้

# ------------------------------------------------------------
# ✏️ เพิ่ม / ลบ / แก้ไข ข้อในเกมประเภท Fill in the Blank
# ------------------------------------------------------------
@admin_bp.route("/add_fill_item/<int:game_id>", methods=["GET", "POST"])
@login_required
def add_fill_item(game_id):
    game = Game.query.get_or_404(game_id)

    if request.method == "POST":
        sentence = request.form.get("sentence")
        correct_word = request.form.get("correct_word")

        if not sentence or not correct_word:
            flash("⚠️ กรุณากรอกข้อมูลให้ครบ", "warning")
            return redirect(request.url)

        # ✅ ต้องเพิ่ม lesson_id เพื่อให้ไม่เป็น NULL
        new_item = FillInBlank(
            lesson_id=game.lesson_id,   # ✅ เพิ่มตรงนี้
            game_id=game.id,
            sentence=sentence,
            correct_word=correct_word
        )

        db.session.add(new_item)
        db.session.commit()
        flash("✅ เพิ่มข้อเติมคำเรียบร้อยแล้ว", "success")
        return redirect(url_for("admin.view_game_detail", game_id=game.id))

    return render_template("add_fill_item.html", game=game)

@admin_bp.route("/game/<int:game_id>/edit_fill_item/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_fill_item(game_id, item_id):
    if not admin_only():
        return redirect("/")

    game = Game.query.get_or_404(game_id)
    item = FillInBlank.query.get_or_404(item_id)

    if request.method == "POST":
        sentence = request.form.get("sentence")
        correct_word = request.form.get("correct_word")

        if not correct_word or correct_word.strip() == "":
            flash("⚠️ กรุณากรอกคำตอบก่อนบันทึก", "warning")
            return redirect(request.url)

        item.sentence = sentence
        item.correct_word = correct_word
        db.session.commit()

        flash("✅ บันทึกการแก้ไขเรียบร้อยแล้ว", "success")

        # ✅ กลับไปหน้ารายละเอียดเกมเติมคำ
        return redirect(url_for("admin.view_game_detail", game_id=game_id))

    return render_template("admin_edit_fill_item.html", game=game, item=item)


@admin_bp.route("/game/<int:game_id>/delete_fill_item/<int:item_id>", methods=["POST"])
@login_required
def delete_fill_item(game_id, item_id):
    if not admin_only():
        return redirect("/")

    item = FillInBlank.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash("🗑️ ลบข้อเติมคำเรียบร้อยแล้ว", "success")
    return redirect(url_for("admin.view_game_detail", game_id=game_id))
# ------------------------------------------------------------
# ✏️ เพิ่ม / ลบ / แก้ไข ข้อในเกมประเภท Scramble (เรียงคำ)
# ------------------------------------------------------------
@admin_bp.route("/game/<int:game_id>/add_scramble_item", methods=["GET", "POST"])
@login_required
def add_scramble_item(game_id):
    if not admin_only():
        return redirect("/")

    game = Game.query.get_or_404(game_id)

    if request.method == "POST":
        sentence = request.form.get("sentence")  # มาจาก textarea
        words = request.form.getlist("words[]")  # มาจาก hidden inputs

        if not sentence or not words:
            flash("⚠️ กรุณากรอกประโยคก่อนบันทึก", "warning")
            return redirect(request.url)

        # เก็บเป็น JSON string เช่น ["I","am","a","student."]
        import json
        sentence_json = json.dumps(words, ensure_ascii=False)

        new_item = ScrambleItem(
            game_id=game.id,
            sentence_json=sentence_json,
            language=request.form.get("lang", "en")
        )
        db.session.add(new_item)
        db.session.commit()
        flash("✅ เพิ่มประโยคเรียงคำเรียบร้อยแล้ว", "success")
    return redirect(url_for("admin.game_detail_speech", game_id=game_id))  # ✅ อยู่หน้าเดิม

    return render_template("add_scramble_item.html", game=game)

@admin_bp.route("/game/<int:game_id>/edit_scramble_item/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_scramble_item(game_id, item_id):
    if not admin_only():
        return redirect("/")

    game = Game.query.get_or_404(game_id)
    item = ScrambleItem.query.get_or_404(item_id)

    if request.method == "POST":
        item.sentence = request.form["sentence"]
        item.correct_order = request.form["correct_order"]
        db.session.commit()
        flash("✏️ แก้ไขประโยคเรียบร้อยแล้ว", "success")
        return redirect(url_for("admin.view_game_detail", game_id=game_id))

    return render_template("edit_scramble_item.html", game=game, item=item)


@admin_bp.route("/game/<int:game_id>/delete_scramble_item/<int:item_id>", methods=["POST"])
@login_required
def delete_scramble_item(game_id, item_id):
    if not admin_only():
        return redirect("/")

    item = ScrambleItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash("🗑️ ลบประโยคเรียบร้อยแล้ว", "success")
    return redirect(url_for("admin.view_game_detail", game_id=game_id))

# ------------------------------------------------------------
# ✏️ เพิ่ม / ลบ / แก้ไข ข้อในเกมประเภท Choice (เลือกคำตอบ)
# ------------------------------------------------------------
@admin_bp.route("/game/<int:game_id>/add_choice_item", methods=["GET", "POST"])
@login_required
def add_choice_item(game_id):
    if not admin_only():
        return redirect("/")

    game = Game.query.get_or_404(game_id)

    if request.method == "POST":
        question = request.form["question"]
        choice_a = request.form["choice_a"]
        choice_b = request.form["choice_b"]
        choice_c = request.form["choice_c"]
        choice_d = request.form["choice_d"]
        correct_choice = request.form["correct_choice"]

        new_item = ChoiceItem(
            game_id=game_id,
            question=question,
            choice_a=choice_a,
            choice_b=choice_b,
            choice_c=choice_c,
            choice_d=choice_d,
            correct_choice=correct_choice
        )
        db.session.add(new_item)
        db.session.commit()
        flash("✅ เพิ่มคำถามแบบเลือกสำเร็จ", "success")
        return redirect(url_for("admin.view_game_detail", game_id=game_id))

    return render_template("add_choice_item.html", game=game)


@admin_bp.route("/game/<int:game_id>/edit_choice_item/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_choice_item(game_id, item_id):
    if not admin_only():
        return redirect("/")

    game = Game.query.get_or_404(game_id)
    item = ChoiceItem.query.get_or_404(item_id)

    if request.method == "POST":
        item.question = request.form["question"]
        item.choice_a = request.form["choice_a"]
        item.choice_b = request.form["choice_b"]
        item.choice_c = request.form["choice_c"]
        item.choice_d = request.form["choice_d"]
        item.correct_choice = request.form["correct_choice"]
        db.session.commit()
        flash("✏️ แก้ไขคำถามเรียบร้อยแล้ว", "success")
        return redirect(url_for("admin.view_game_detail", game_id=game_id))

    return render_template("edit_choice_item.html", game=game, item=item)


@admin_bp.route("/game/<int:game_id>/delete_choice_item/<int:item_id>", methods=["POST"])
@login_required
def delete_choice_item(game_id, item_id):
    if not admin_only():
        return redirect("/")

    item = ChoiceItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash("🗑️ ลบคำถามเรียบร้อยแล้ว", "success")
    return redirect(url_for("admin.view_game_detail", game_id=game_id))

@admin_bp.route("/lesson/<int:lesson_id>/add_question", methods=["GET", "POST"])
@login_required
def add_question(lesson_id):
    if not admin_only():
        return redirect("/")

    lesson = Lesson.query.get_or_404(lesson_id)

    if request.method == "POST":
        question = request.form["question"]
        correct_option = request.form["correct_option"]
        lang = request.form["lang"]
        question_type = request.form.get("question_type", "test")

        new_q = Exercise(
            lesson_id=lesson_id,
            question=question,
            correct_option=correct_option,
            question_type=question_type,
            lang=lang
        )
        db.session.add(new_q)
        db.session.commit()
        flash("✅ เพิ่มคำถามแบบทดสอบสำเร็จ", "success")
        return redirect(url_for("admin.lesson_tests", lesson_id=lesson_id))

    return render_template("add_question.html", lesson=lesson)


@admin_bp.route("/lesson/<int:lesson_id>/edit_question/<int:q_id>", methods=["GET", "POST"])
@login_required
def edit_question(lesson_id, q_id):
    if not admin_only():
        return redirect("/")

    lesson = Lesson.query.get_or_404(lesson_id)
    question = Exercise.query.get_or_404(q_id)

    if request.method == "POST":
        question.question = request.form["question"]
        question.correct_option = request.form["correct_option"]
        question.lang = request.form["lang"]
        question.question_type = request.form.get("question_type", "test")
        db.session.commit()
        flash("✏️ แก้ไขคำถามเรียบร้อย", "success")
        return redirect(url_for("admin.lesson_tests", lesson_id=lesson_id))

    return render_template("edit_question.html", lesson=lesson, question=question)


@admin_bp.route("/lesson/<int:lesson_id>/delete_question/<int:q_id>", methods=["POST"])
@login_required
def delete_question(lesson_id, q_id):
    if not admin_only():
        return redirect("/")

    question = Exercise.query.get_or_404(q_id)
    db.session.delete(question)
    db.session.commit()
    flash("🗑️ ลบคำถามสำเร็จ", "success")
    return redirect(url_for("admin.lesson_tests", lesson_id=lesson_id))

@admin_bp.route("/add_quiz_item/<int:game_id>", methods=["GET", "POST"])
@login_required
def add_quiz_item(game_id):
    if not admin_only():
        return redirect("/")

    game = Game.query.get_or_404(game_id)
    lesson = game.lesson

    if request.method == "POST":
        question = request.form.get("question")
        option_a = request.form.get("option_a")
        option_b = request.form.get("option_b")
        option_c = request.form.get("option_c")
        option_d = request.form.get("option_d")
        correct = request.form.get("correct")

        new_item = Exercise(
            lesson_id=lesson.id,
            question=question,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct=correct.strip().upper(),  # ✅ เก็บเป็น A/B/C/D
            question_type="game",
            lang=game.lang
        )
        db.session.add(new_item)
        db.session.commit()
        flash("✅ เพิ่มคำถามควิซสำเร็จ", "success")
        return redirect(url_for("admin.view_game_detail", game_id=game.id))

    return render_template("add_quiz_item.html", game=game)


@admin_bp.route("/quiz/edit/<int:game_id>/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_quiz_item(game_id, item_id):
    if not admin_only():
        return redirect("/")

    game = Game.query.get_or_404(game_id)
    item = Exercise.query.get_or_404(item_id)

    if request.method == "POST":
        item.question = request.form["question"]
        item.option_a = request.form["option_a"]
        item.option_b = request.form["option_b"]
        item.option_c = request.form["option_c"]
        item.option_d = request.form["option_d"]
        item.correct = request.form["correct"]

        db.session.commit()
        flash("✅ แก้ไขคำถามเรียบร้อย", "success")
        return redirect(url_for("admin.view_game_detail", game_id=game.id))

    return render_template("quiz_item_edit.html", game=game, item=item)

@admin_bp.route("/quiz/delete/<int:game_id>/<int:item_id>", methods=["POST"])
@login_required
def delete_quiz_item(game_id, item_id):
    # ตรวจสิทธิ์เฉพาะผู้ดูแลระบบเท่านั้น
    if (current_user.role or "").lower() != "admin":
        flash("❌ เฉพาะผู้ดูแลระบบเท่านั้นที่เข้าหน้านี้ได้", "danger")
        return redirect(url_for("admin.dashboard"))

    # ดึงข้อมูลเกมและคำถาม
    game = Game.query.get_or_404(game_id)
    item = Exercise.query.get_or_404(item_id)  # ✅ ใช้ Exercise สำหรับเก็บ quiz

    # ลบออกจากฐานข้อมูล
    db.session.delete(item)
    db.session.commit()

    flash("🗑️ ลบคำถามควิซเรียบร้อยแล้ว", "success")
    return redirect(url_for("admin.view_game_detail", game_id=game.id))
from flask import send_from_directory

@admin_bp.route('/uploads/<path:filename>')
def serve_upload(filename):
    upload_folder = os.path.join('static', 'uploads')
    return send_from_directory(upload_folder, filename)