from .auth import auth_bp
from .admin import admin_bp
from .teacher import teacher_bp
from .student import student_bp
from .game import game_bp
from .admin_quiz import admin_quiz_bp

def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(game_bp)
    app.register_blueprint(admin_quiz_bp)
