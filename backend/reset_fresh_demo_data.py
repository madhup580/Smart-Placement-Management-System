"""
Reset the database to fresh demo data.

This removes existing users, attempts, submissions, resources, questions,
quizzes, assessments, posts, notifications, and related records, then seeds
the demo coding questions, non-technical questions, quiz, assessment, and notes.
"""
from flask import Flask
from sqlalchemy import text

from config import Config
from models import db
from seed_data import seed_initial_data


def reset_database():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        db.create_all()

        engine_name = db.engine.dialect.name
        if engine_name == "mysql":
            db.session.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        elif engine_name == "sqlite":
            db.session.execute(text("PRAGMA foreign_keys=OFF"))

        for table in reversed(list(db.metadata.tables.values())):
            if engine_name == "mysql":
                db.session.execute(text(f"TRUNCATE TABLE `{table.name}`"))
            else:
                db.session.execute(table.delete())

        if engine_name == "mysql":
            db.session.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        elif engine_name == "sqlite":
            db.session.execute(text("PRAGMA foreign_keys=ON"))

        db.session.commit()
        seed_initial_data()


if __name__ == "__main__":
    reset_database()
    print("[Reset] Database cleared and fresh demo data added.")
