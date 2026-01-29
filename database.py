import datetime
import hashlib
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import json

DB_NAME = "tutor.db"
engine = create_engine(f"sqlite:///{DB_NAME}", echo=False)
Base = declarative_base()
Session = sessionmaker(bind=engine)


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    display_name = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    skill_profile = relationship("UserSkill", back_populates="user", uselist=False)
    attempts = relationship("Attempt", back_populates="user")


class UserSkill(Base):
    __tablename__ = 'user_skills'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))

    loops = Column(Float, default=0.0)
    recursion = Column(Float, default=0.0)
    syntax = Column(Float, default=0.0)
    logic = Column(Float, default=0.0)
    data_structures = Column(Float, default=0.0)

    user = relationship("User", back_populates="skill_profile")


class Attempt(Base):
    __tablename__ = 'attempts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    session_id = Column(String)
    snippet_id = Column(String)
    user_code = Column(String)
    is_success = Column(Boolean)
    rewards_json = Column(String, default="{}")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="attempts")


def init_db():
    """Creates the tables if they don't exist."""
    Base.metadata.create_all(engine)
    print(f"✅ Database '{DB_NAME}' initialized.")


def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(username, password, display_name):
    session = Session()
    if session.query(User).filter_by(username=username).first():
        session.close()
        return False, "Username already exists."

    new_user = User(
        username=username,
        password_hash=hash_pass(password),
        display_name=display_name
    )
    session.add(new_user)
    session.commit()

    new_skills = UserSkill(user_id=new_user.id)
    session.add(new_skills)
    session.commit()

    session.close()
    return True, "Registration successful!"


def login_user(username, password):
    session = Session()
    user = session.query(User).filter_by(
        username=username,
        password_hash=hash_pass(password)
    ).first()

    if user:
        user_data = {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name
        }
        session.close()
        return user_data
    session.close()
    return None


def log_attempt(user_id, snippet_id, code, success, session_id=None, rewards=None):
    session = Session()
    attempt = Attempt(
        user_id=user_id,
        snippet_id=snippet_id,
        user_code=code,
        is_success=success,
        session_id=session_id or "unknown",
        rewards_json=json.dumps(rewards) if rewards else "{}"
    )
    session.add(attempt)
    session.commit()
    session.close()


def get_user_skills(user_id):
    """Returns the user's skill vector as a dictionary."""
    session = Session()
    skills = session.query(UserSkill).filter_by(user_id=user_id).first()

    if not skills:
        session.close()
        return None

    vector = {
        "Loops": skills.loops,
        "Recursion": skills.recursion,
        "Syntax": skills.syntax,
        "Logic": skills.logic,
        "Data_Structures": skills.data_structures
    }
    session.close()
    return vector


def update_user_skills(user_id, skill_updates):
    """
    Updates specific skills for a user.
    skill_updates: dict, e.g., {"Syntax": 2.0, "Loops": 1.0}
    """
    session = Session()
    skills = session.query(UserSkill).filter_by(user_id=user_id).first()

    if skills:
        if "Loops" in skill_updates: skills.loops = skill_updates["Loops"]
        if "Recursion" in skill_updates: skills.recursion = skill_updates["Recursion"]
        if "Syntax" in skill_updates: skills.syntax = skill_updates["Syntax"]
        if "Logic" in skill_updates: skills.logic = skill_updates["Logic"]
        if "Data_Structures" in skill_updates: skills.data_structures = skill_updates["Data_Structures"]

        session.commit()
    session.close()


def get_user_stats(user_id):
    """Returns total attempts and success count."""
    session = Session()
    total = session.query(Attempt).filter_by(user_id=user_id).count()
    success = session.query(Attempt).filter_by(user_id=user_id, is_success=True).count()
    session.close()
    return {"total": total, "success": success}


def get_user_history(user_id, limit=10):
    """Returns the last N attempts for the dashboard history."""
    session = Session()
    attempts = session.query(Attempt).filter_by(user_id=user_id).order_by(Attempt.timestamp.desc()).limit(limit).all()

    history = []
    for a in attempts:
        history.append({
            "id": a.snippet_id,
            "code": a.user_code,
            "status": "✅ Solved" if a.is_success else "❌ Failed",
            "time": a.timestamp.strftime("%Y-%m-%d %H:%M")
        })
    session.close()
    return history


def get_last_unfinished(user_id):
    """Finds the most recent failed attempt to allow 'Resuming'."""
    session = Session()
    last = session.query(Attempt).filter_by(user_id=user_id).order_by(Attempt.timestamp.desc()).first()
    session.close()

    if last and not last.is_success:
        return {"code": last.user_code, "id": last.snippet_id}
    return None


def get_user_sessions(user_id):
    """Returns a list of unique sessions with their status."""
    session = Session()
    unique_ids = session.query(Attempt.session_id).filter_by(user_id=user_id).distinct().all()

    sessions = []
    for (sid,) in unique_ids:
        if sid == "unknown": continue
        attempts = session.query(Attempt).filter_by(session_id=sid).order_by(Attempt.timestamp.asc()).all()
        if not attempts: continue

        first_attempt = attempts[0]
        is_solved = any(a.is_success for a in attempts)

        sessions.append({
            "session_id": sid,
            "timestamp": first_attempt.timestamp,
            "initial_code": first_attempt.user_code,
            "status": "✅ Solved" if is_solved else "❌ Unsolved",
            "attempts_count": len(attempts)
        })

    session.close()
    sessions.sort(key=lambda x: x["timestamp"], reverse=True)
    return sessions


def get_session_history(session_id):
    """Returns all attempts for a specific session."""
    session = Session()
    attempts = session.query(Attempt).filter_by(session_id=session_id).order_by(Attempt.timestamp.asc()).all()
    history = []
    for a in attempts:
        rewards = json.loads(a.rewards_json) if a.rewards_json else {}
        history.append({
            "code": a.user_code,
            "success": a.is_success,
            "time": a.timestamp.strftime("%H:%M:%S"),
            "rewards": rewards
        })
    session.close()
    return history


def get_user_progress_data(user_id):
    """Returns list of all score updates over time."""
    session = Session()
    # Get all successful attempts chronologically
    attempts = session.query(Attempt).filter_by(user_id=user_id, is_success=True).order_by(
        Attempt.timestamp.asc()).all()

    data = []
    for a in attempts:
        data.append({
            "timestamp": a.timestamp,
            "session_id": a.session_id,
            "rewards": json.loads(a.rewards_json) if a.rewards_json else {}
        })
    session.close()
    return data


# Initialize tables immediately when imported
init_db()