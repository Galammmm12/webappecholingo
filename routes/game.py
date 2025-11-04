from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import (
    db, Game, GameItem, ChoiceItem, FillInBlank, MatchingItem,
    ScrambleItem, SpeechQuestion, GameScore, Exercise, QuizResult, SpeechResult
)
import random, tempfile, os, time
import whisper
from sentence_transformers import SentenceTransformer, util

game_bp = Blueprint("game", __name__, url_prefix="/game")
whisper_model = whisper.load_model("base")
embedder = SentenceTransformer("paraphrase-MiniLM-L6-v2")

def get_theme_for_game(game):
    return {"bg_color": "#f9f9f9", "accent": "#1976d2"}

def save_game_score(user_id, game_id, score):
    record = GameScore.query.filter_by(user_id=user_id, game_id=game_id).first()
    if record:
        record.score = max(record.score, score)
    else:
        db.session.add(GameScore(user_id=user_id, game_id=game_id, score=score))
    db.session.commit()


@game_bp.route("/play/<int:game_id>", methods=["GET", "POST"])
@login_required
def play_game(game_id):
    game = Game.query.get_or_404(game_id)
    gtype = (game.game_type or "").lower().strip()
    lang = game.lang or "en"
    theme = get_theme_for_game(game)

    score_url = (
        url_for("student.lesson_score_detail_zh", lesson_id=game.lesson_id)
        if lang == "zh" else url_for("student.lesson_score_detail", lesson_id=game.lesson_id)
    )

    record = GameScore.query.filter_by(user_id=current_user.id, game_id=game.id).first()
    played = bool(record and not getattr(current_user, "allow_retake_game", False))

    
    if gtype in ["matching", "จับคู่"]:
        items = MatchingItem.query.filter_by(game_id=game.id).all()
        if played:
            return redirect(score_url)

        if request.method == "POST":
            score = int(request.form.get("score", 0))
            save_game_score(current_user.id, game.id, score)

            correct_pairs = [
                {"question": i.question_text, "answer": i.answer_text}
                for i in items
            ]

            return render_template(
                "matching_result.html",
                game=game,
                score=score,
                total=len(items),
                correct_pairs=correct_pairs,
                theme=theme,
                lang=lang
            )

        answers = items[:]
        random.shuffle(answers)
        return render_template("play_matching.html", game=game, items=items, answers=answers,
                               theme=theme, played=played, lang=lang , lesson=game.lesson)

    
    elif gtype in ["drag", "drag drop"]:
        items = GameItem.query.filter_by(game_id=game.id).all()
        if played:
            return redirect(score_url)

        words = [i.correct_word for i in items]
        random.shuffle(words)
        pinyin_map = {i.correct_word: i.pinyin or "" for i in items}

        return render_template(
            "play_drag.html",
            game=game,
            items=items,
            shuffled_words=words,
            pinyin_map=pinyin_map,
            theme=theme,
            played=played,
            lang=lang,
            lesson=game.lesson  # ✅ ส่ง lesson ให้ template
        )



    elif gtype in ["fill", "fill-in-the-blank", "เติมคำ"]:
        items = FillInBlank.query.filter_by(game_id=game.id).all()
        if played:
            return redirect(score_url)

        
        hint_words = []
        for it in items:
            if it.correct_word:
                hint_words += [w.strip() for w in it.correct_word.split(";")]
        hint_words = list(set(hint_words))  
        random.shuffle(hint_words)

        
        if request.method == "POST":
            score, results = 0, []
            for it in items:
                ans = request.form.get(f"q{it.id}", "").strip().lower()
                corrects = [c.strip().lower() for c in it.correct_word.split(";")]
                ok = ans in corrects
                if ok:
                    score += 1
                results.append({
                    "sentence": it.sentence,
                    "user_answer": ans,
                    "correct_answer": corrects[0],
                    "is_correct": ok
                })

            save_game_score(current_user.id, game.id, score)
            return render_template(
                "fill_result.html",
                game=game,
                results=results,
                hint_words=hint_words,  
                correct_answers=[r["correct_answer"] for r in results],
                score=score,
                total=len(items),
                theme=theme,
                lang=lang
            )

        
        return render_template(
            "play_fill.html",
            game=game,
            items=items,
            hint_words=hint_words,  
            theme=theme,
            played=played,
            lang=lang
        )

    elif gtype in ["scramble", "sentence scramble", "เรียงคำ"]:
        items = ScrambleItem.query.filter_by(game_id=game.id).all()
        if played:
            return redirect(score_url)

        if request.method == "POST":
            score, results = 0, []
            for it in items:
                correct = it.words
                ans = (request.form.get(f"q{it.id}") or "").split("|")
                ok = ans == correct
                if ok:
                    score += 1
                results.append({
                    "question": " ".join(correct),
                    "user_answer": " ".join(ans),
                    "correct_answer": " ".join(correct),
                    "is_correct": ok
                })

            save_game_score(current_user.id, game.id, score)
            return render_template(
                "scramble_result.html",
                game=game,
                results=results,
                
                score=score,
                total=len(items),
                theme=theme,
                lang=lang
            )

        scrambled = [{"id": it.id, "words": random.sample(it.words, len(it.words))} for it in items]
        return render_template("play_scramble.html", game=game, scrambled=scrambled,
                               theme=theme, played=played, lang=lang)

    
    elif gtype in ["choice", "choice_match", "ช้อยส์"]:
        items = ChoiceItem.query.filter_by(game_id=game.id).all()
        if played:
            return redirect(score_url)

        display = []
        for it in items:
            opts = it.options.split(";") if it.options else []
            random.shuffle(opts)
            display.append({"item": it, "options": opts})

        if request.method == "POST":
            score, results = 0, []
            for it in items:
                ans = (request.form.get(f"q{it.id}") or "").strip()
                correct = it.correct.strip()
                ok = ans.lower() == correct.lower()
                if ok:
                    score += 1
                results.append({
                    "question": it.prompt_text,
                    "user_answer": ans,
                    "correct_answer": correct,
                    "is_correct": ok
                })

            save_game_score(current_user.id, game.id, score)
            return render_template(
                "choice_result.html",
                game=game,
                results=results,
                score=score,
                total=len(items),
                theme=theme,
                lang=lang
            )

        return render_template("play_choice_match.html", game=game, display=display,
                               theme=theme, played=played, lang=lang)

   
    elif gtype in ["quiz", "exam", "test", "แบบทดสอบ"]:
        # ✅ ตรวจว่าผู้ใช้เคยเล่นแล้วหรือยัง
        record = GameScore.query.filter_by(user_id=current_user.id, game_id=game.id).first()
        if record and not current_user.allow_retake_game:
            flash("คุณเคยทำแบบทดสอบนี้แล้ว ✅", "info")
            # 👉 ไปหน้าผลคะแนน quiz
            return redirect(url_for("student.lesson_score_detail", lesson_id=game.lesson_id))

        
        items = Exercise.query.filter_by(
            lesson_id=game.lesson_id,
            question_type="game",  
            lang=game.lang
        ).all()

        #  เมื่อผู้ใช้ส่งคำตอบ
        if request.method == "POST":
            user_answers = {}
            correct_answers = {}
            results = []
            score = 0

            for it in items:
                user_ans = request.form.get(f"q{it.id}", "").strip().upper()
                correct = (it.correct_option or "").strip().upper()
                user_answers[it.id] = user_ans
                correct_answers[it.id] = correct
                ok = user_ans == correct
                if ok:
                    score += 1
                results.append({
                    "question": it.question,
                    "user_answer": user_ans,
                    "correct_answer": correct,
                    "is_correct": ok,
                    "option_a": it.option_a,
                    "option_b": it.option_b,
                    "option_c": it.option_c,
                    "option_d": it.option_d,
                })

            #  บันทึกคะแนน
            save_game_score(current_user.id, game.id, score)

            #  แสดงหน้าเฉลย
            return render_template(
                "quiz_answer.html",
                game=game,  score=score, total=len(items),items=items,results=results, user_answers=user_answers, correct_answers=correct_answers,
                theme=theme,  lesson=game.lesson,   lang=lang
            )
            #  ยังไม่เคยทำ → แสดงหน้า quiz
        return render_template(
            "play_quiz.html",
            game=game,
            items=items,
            theme=theme,
            lang=lang
        )

    elif gtype in ["speech", "speaking", "speaking game", "พูด", "พูดคุย"]:


        questions = SpeechQuestion.query.filter_by(game_id=game.id).all()
        if played:
            return redirect(score_url)
        random.shuffle(questions)

        if lang == "zh":
            pinyin_map = {
                q.correct_answer: getattr(q, "pinyin", "") or getattr(q, "pinyin_text", "") or ""
                for q in questions
            }
        else:
            pinyin_map = {}

        return render_template(
            "play_speech.html",
            game=game,
            questions=questions,
            pinyin_map=pinyin_map,
            theme=theme,
            played=played,
            lang=lang
        )

@game_bp.route("/speech_upload", methods=["POST"])
@login_required
def speech_upload():
    from werkzeug.utils import secure_filename
    audio = request.files.get("audio")
    qid = request.form.get("question_id")
    lang = request.form.get("lang", "en")

    if not audio or not qid:
        return jsonify({"success": False, "message": "ข้อมูลไม่ครบ"})

    tmp_dir = os.path.join(tempfile.gettempdir(), "speech_uploads")
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_path = os.path.join(tmp_dir, secure_filename(f"speech_{int(time.time()*1000)}.webm"))

    try:
        audio.save(tmp_path)
        for _ in range(50):
            if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 1000:
                break
            time.sleep(0.1)

        lang_code = "zh" if "zh" in lang.lower() else "en"
        result = whisper_model.transcribe(tmp_path, fp16=False, language=lang_code)
        transcript = result.get("text", "").strip()
    except Exception as e:
        return jsonify({"success": False, "message": f"Whisper error: {e}"})
    finally:
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except Exception: pass

    question = SpeechQuestion.query.get(int(qid))
    if not question:
        return jsonify({"success": False, "message": "ไม่พบคำถาม"})

    correct = question.correct_answer or ""
    emb1 = embedder.encode(transcript, convert_to_tensor=True)
    emb2 = embedder.encode(correct, convert_to_tensor=True)
    similarity = float(util.cos_sim(emb1, emb2))

    db.session.add(SpeechResult(
        user_id=current_user.id,
        question_id=qid,
        spoken_text=transcript,
        similarity_score=similarity,
        is_correct=similarity >= 0.7,
        audio_path=None
    ))
    db.session.commit()

    return jsonify({"success": True, "transcript": transcript, "similarity": round(similarity, 3)})


@game_bp.route("/speech_finish/<int:game_id>", methods=["POST"])
@login_required
def speech_finish(game_id):
    """รับคะแนนรวมจากหน้าเว็บเกมพูด แล้วบันทึกลงฐานข้อมูล"""
    try:
        data = request.get_json() or {}
        score = int(data.get("score", 0))
        total = int(data.get("total", 0))

        
        q_ids = [q.id for q in SpeechQuestion.query.filter_by(game_id=game_id).all()]
        if q_ids:
            SpeechResult.query.filter(
                SpeechResult.user_id == current_user.id,
                SpeechResult.question_id.in_(q_ids)
            ).delete(synchronize_session=False)
            db.session.commit()

        
        save_game_score(current_user.id, game_id, score)

        return jsonify({"success": True, "score": score, "total": total})
    except Exception as e:
        db.session.rollback()
        print("❌ speech_finish error:", e)
        return jsonify({"success": False, "message": f"เกิดข้อผิดพลาด: {e}"})


@game_bp.route("/speech_result/<int:game_id>")
@login_required
def speech_result(game_id):
    game = Game.query.get_or_404(game_id)
    record = GameScore.query.filter_by(user_id=current_user.id, game_id=game.id).first()
    score = record.score if record else 0
    total = SpeechQuestion.query.filter_by(game_id=game.id).count()
    percentage = round((score / total) * 100, 2) if total > 0 else 0
    return render_template("speech_result.html", game=game, score=score, total=total, percentage=percentage)


@game_bp.route("/save_score/<int:game_id>", methods=["POST"])
@login_required
def save_score(game_id):
    """บันทึกคะแนนที่ผู้ใช้ทำได้ (ใช้ได้ทุกประเภทเกม)"""
    try:
        score = request.form.get("score") or (request.get_json() or {}).get("score")
        if score is None:
            return jsonify({"success": False, "message": "ไม่พบคะแนนที่ส่งมา"})
        score = int(score)
        save_game_score(current_user.id, game_id, score)
        return jsonify({"success": True, "message": "บันทึกคะแนนสำเร็จ"})
    except Exception as e:
        db.session.rollback()
        print("❌ Error saving score:", e)
        return jsonify({"success": False, "message": f"เกิดข้อผิดพลาด: {e}"})
    
    

@game_bp.route("/quiz_result/<int:game_id>")
@login_required
def quiz_result_page(game_id):
    game = Game.query.get_or_404(game_id)
    lang = game.lang or "en"
    record = GameScore.query.filter_by(user_id=current_user.id, game_id=game.id).first()
    score = record.score if record else 0

    # ดึงคำถามเพื่อแสดงเฉลย
    items = Exercise.query.filter_by(
        lesson_id=game.lesson_id,
        question_type="game",
        lang=lang
    ).all()

    results = []
    for it in items:
        results.append({
            "question": it.question,
            "user_answer": "-",  
            "correct_answer": it.correct_option,
            "option_a": it.option_a,
            "option_b": it.option_b,
            "option_c": it.option_c,
            "option_d": it.option_d,
            "is_correct": None
        })

    return render_template(
        "quiz_answer.html",   
        game=game,
        score=score,
        total=len(items),
        results=results,
        lesson=game.lesson,
        lang=lang
    )
