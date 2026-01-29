import streamlit as st
import random
import pandas as pd
import plotly.express as px
import google.generativeai as genai
from retriever import CodeRetriever
import config
import database
import analytics
import uuid
import ast
import itertools

# Constant list of calibration code snippets
CALIBRATION_TEST = [
    {
        "id": "calib_01",
        "topic": "Syntax",
        "code": "def greet(name)\n    print('Hello ' + name)",
        "hint": "Focus on the function definition line. Python requires a specific symbol at the end.",
        "reward": {"Syntax": 2.0, "Logic": 1.0}
    },
    {
        "id": "calib_02",
        "topic": "Loops",
        "code": "count = 0\nwhile count < 3:\n    print(count)",
        "hint": "This loop runs forever because the condition never becomes False. How do you change 'count'?",
        "reward": {"Loops": 2.0, "Logic": 1.0}
    },
    {
        "id": "calib_03",
        "topic": "Recursion",
        "code": "def fact(n):\n    return n * fact(n-1)",
        "hint": "Infinite recursion! You need a 'base case' to stop calling the function when n reaches 0 or 1.",
        "reward": {"Recursion": 2.0, "Logic": 1.0}
    },
    {
        "id": "calib_04",
        "topic": "Conditionals",
        "code": "x = 10\nif x = 10:\n    print('Equal')",
        "hint": "In Python, a single '=' is for assignment. What do we use for comparison?",
        "reward": {"Logic": 2.0, "Syntax": 1.0}
    },
    {
        "id": "calib_05",
        "topic": "Data Structures",
        "code": "my_list = [1, 2, 3]\nprint(my_list[3])",
        "hint": "Lists are 0-indexed. The last item is at index 2. Index 3 is out of bounds.",
        "reward": {"Data_Structures": 2.0, "Logic": 1.0}
    }
]


# Gemini and Retriever setup
def get_next_api_key():
    if "key_cycle" not in st.session_state:
        st.session_state.key_cycle = itertools.cycle(config.GEMINI_KEYS)
    return next(st.session_state.key_cycle)


def generate_content_with_rotation(prompt):
    """Tries to generate content, rotating keys on failure."""
    attempts = 0
    max_attempts = len(config.GEMINI_KEYS)

    while attempts < max_attempts:
        current_key = get_next_api_key()
        try:
            genai.configure(api_key=current_key)
            models = [m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods]

            models.sort(key=lambda x: "flash" in x.lower(), reverse=True)
            if not models:
                raise Exception("No generative models found for this API key.")

            target_model_name = models[0]

            model = genai.GenerativeModel(target_model_name)
            response = model.generate_content(prompt)
            return response

        except Exception as e:
            print(f"⚠️ Key failed: {str(e)[:50]}... Rotation to next.")
            attempts += 1

    raise Exception("All API keys failed.")


def configure_gemini():
    """
    Tries to find at least one working key at startup.
    Returns: (True, model_name) if any key works, else (False, None).
    """
    if not hasattr(config, 'GEMINI_KEYS') or not config.GEMINI_KEYS:
        return False, None

    # Try every key until one works
    for key in config.GEMINI_KEYS:
        try:
            genai.configure(api_key=key)
            models = [m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods]
            models.sort(key=lambda x: "flash" in x.lower(), reverse=True)
            if models:
                print(f"✅ Startup Success with key ending in ...{key[-4:]}")
                return True, models[0]
        except Exception:
            continue

    # If we are here all keys failed
    print("❌ All API keys failed at startup.")
    return False, None


# Initializes
@st.cache_resource
def load_cached_retriever():
    return CodeRetriever()


HAS_GEMINI, MODEL_NAME = configure_gemini()
try:
    retriever = load_cached_retriever()
except Exception as e:
    st.error(f"Backend Error: {e}")
    st.stop()


# Helper functions
def get_player_profile(skills):
    if not skills:
        return {"level": 0, "title": "Novice", "total_xp": 0}

    avg_xp = sum(skills.values()) / 5.0
    level = int(avg_xp)

    # Title
    best_skill = max(skills, key=skills.get)
    best_val = skills[best_skill]

    if best_val < 5:
        suffix = "Novice"
    elif best_val < 10:
        suffix = "Apprentice"
    elif best_val < 20:
        suffix = "Adept"
    elif best_val < 40:
        suffix = "Master"
    else:
        suffix = "Grandmaster"

    return {
        "level": level,
        "title": f"{best_skill} {suffix}",
        "total_xp": round(avg_xp, 1)
    }


def get_required_skill_for_topic(topic):
    topic_lower = topic.lower()
    if "loop" in topic_lower:
        return "Loops"
    if "recursion" in topic_lower:
        return "Recursion"
    if "list" in topic_lower or "dict" in topic_lower or "class" in topic_lower:
        return "Data_Structures"
    if "syntax" in topic_lower:
        return "Syntax"
    return "Logic"


def is_problem_locked(snippet, user_skills):
    """Returns True if the user doesn't meet the skill requirement."""
    difficulty = snippet.get('difficulty', 'Novice')
    topic = snippet.get('topic', 'General')

    # Novice is always unlocked
    if difficulty == "Novice":
        return False

    req_skill_name = get_required_skill_for_topic(topic)
    user_skill_val = user_skills.get(req_skill_name, 0.0)

    if difficulty == "Intermediate" and user_skill_val < 5.0:
        return True
    if difficulty == "Advanced" and user_skill_val < 10.0:
        return True

    return False


def inject_global_css():
    st.markdown(
        """
        <style>
        .stApp {
            background: radial-gradient(1200px circle at 15% 10%, rgba(120, 180, 255, 0.22), transparent 45%),
                        radial-gradient(900px circle at 85% 15%, rgba(255, 150, 220, 0.18), transparent 40%),
                        radial-gradient(1100px circle at 60% 90%, rgba(120, 255, 200, 0.14), transparent 45%),
                        linear-gradient(180deg, rgba(10, 12, 20, 1) 0%, rgba(7, 10, 16, 1) 100%);
        }

        h1, h2, h3 { letter-spacing: -0.02em; }

        .card {
            border: 1px solid rgba(255,255,255,0.08);
            background: rgba(255,255,255,0.04);
            border-radius: 18px;
            padding: 18px 18px 10px 18px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.25);
            margin-bottom: 20px;
        }

        .pill {
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            border: 1px solid rgba(255,255,255,0.10);
            background: rgba(255,255,255,0.05);
            font-size: 12px;
            opacity: 0.92;
            margin-right: 6px;
        }

        [data-testid="stChatMessage"] {
            border-radius: 16px;
            padding: 10px 14px !important;
            border: 1px solid rgba(255,255,255,0.06);
            background: rgba(255,255,255,0.03);
        }

        .stButton > button {
            border-radius: 14px !important;
            padding: 0.55rem 1rem !important;
            border: 1px solid rgba(255,255,255,0.14) !important;
            background: linear-gradient(135deg, rgba(120,180,255,0.22), rgba(255,150,220,0.18)) !important;
            color: rgba(255,255,255,0.92) !important;
            box-shadow: 0 10px 25px rgba(0,0,0,0.18) !important;
            transition: transform .06s ease-in-out, filter .1s ease-in-out;
        }
        .stButton > button:hover { transform: translateY(-1px); filter: brightness(1.05); }
        .stButton > button:active { transform: translateY(0px) scale(0.99); }

        button[kind="primary"] {
            background: linear-gradient(135deg, rgba(120,220,255,0.30), rgba(255,160,220,0.24)) !important;
            border: 1px solid rgba(255,255,255,0.18) !important;
        }

        textarea { border-radius: 14px !important; }

        section[data-testid="stSidebar"] {
            border-right: 1px solid rgba(255,255,255,0.08);
            background: rgba(255,255,255,0.03);
        }

        .lives-container {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def top_header():
    name = st.session_state.get("display_name", "there")
    exp = st.session_state.get("experience", "novice")
    step = st.session_state.get("step", 0)

    if step == "dashboard":
        step_name = "Dashboard"
    elif step == "calibration":
        step_name = "Calibration"
    elif isinstance(step, int):
        step_name = {0: "Login", 1: "Analyze", 2: "Warm-up", 3: "Fix"}.get(step, "Tutor")
    else:
        step_name = "Tutor"

    st.markdown(
        f"""
        <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:10px;">
                <div>
                    <div style="font-size:28px; font-weight:800;">🦉 Hello, {name}!</div>
                    <div style="opacity:0.82; margin-top:2px;">Active learning through Socratic guidance — master the logic, not just the fix.</div>
                </div>
                <div style="text-align:right;">
                    <span class="pill">Phase: {step_name}</span>
                    <span class="pill">Level: {exp}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")


def render_sidebar():
    if st.session_state.get("logged_in") and st.session_state.get("user_id"):
        skills = database.get_user_skills(st.session_state.user_id)
        profile = get_player_profile(skills)
        st.session_state.experience = f"Lvl {profile['level']} | {profile['title']}"

    with st.sidebar:
        st.write("---")
        st.sidebar.markdown(
            f"**User:** {st.session_state.get('display_name', '')}  \n"
            f"**Experience:** {st.session_state.get('experience', 'Novice')}"
        )
        st.sidebar.markdown("---")

        if st.session_state.step not in ["dashboard", "calibration"]:
            if st.button("⬅️ Dashboard", use_container_width=True):
                st.session_state.step = "dashboard"
                st.rerun()

        if st.button("🔄 Restart Session", use_container_width=True):
            st.session_state.step = "dashboard"
            st.session_state.chat = []
            st.session_state.user_code = ""
            st.session_state.analysis = None
            st.session_state.current_session_id = None
            st.rerun()

        if st.button("🚪 Logout", use_container_width=True):
            logout()


def init_session():
    defaults = {
        "logged_in": False,
        "user_id": None,
        "username": "",
        "display_name": "",
        "experience": "novice",
        "step": "dashboard",
        "chat": [],
        "user_code": "",
        "analysis": None,
        "match_index": 0,
        "auth_mode": "Login",
        "current_session_id": None,
        "calib_idx": 0,
        "calib_score": {},
        "calib_attempts": 0,
        "calib_status": "active",
        "calib_feedback": None,
        "calib_feedback_type": None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def check_calibration_needed(user_id):
    skills = database.get_user_skills(user_id)
    if not skills:
        return True
    return sum(skills.values()) == 0


def clear_auth_fields():
    if "auth_username" in st.session_state:
        st.session_state.auth_username = ""
    if "auth_password" in st.session_state:
        st.session_state.auth_password = ""
    if "reg_username" in st.session_state:
        st.session_state.reg_username = ""
    if "reg_password" in st.session_state:
        st.session_state.reg_password = ""
    if "reg_display" in st.session_state:
        st.session_state.reg_display = ""


def get_tutor_response(messages, user_code, context):
    if not HAS_GEMINI:
        return "⚠️ Offline Mode."

    hist = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    user_name = st.session_state.get("display_name", "you")

    prompt = f"""
                You are a Socratic Tutor for Python.

                Current Phase: {context.get('phase', 'Unknown')}
                Address the user by the name: "{user_name}"

                User's Code:
                ```python
                {user_code}
                ```

                Chat History:
                {hist}

                CRITICAL INSTRUCTIONS:
                1. Address the user directly by their name ("{user_name}") — do NOT call them "you".
                2. Be short (Max 2 sentences).
                3. NEVER reveal the answer. Ask a guiding question.
                4. NEVER use terms like "Root", "Taxonomy", "Node", or "Dataset".
                5. If the user is wrong, ask them to check a specific logic concept (e.g., "Check how you are iterating").
                """

    try:
        response = generate_content_with_rotation(prompt)

        if response and response.text:
            return response.text
        return "I'm analyzing your code, but I couldn't generate a specific hint. Try rephrasing?"
    except Exception as e:
        return f"AI Error: {str(e)}"


def ai_judge(original, fix, predicted_error):
    # Check for syntax errors
    try:
        ast.parse(fix)
    except SyntaxError as e:
        return False, f"Syntax Error: {e.msg} at line {e.lineno}"

    if not HAS_GEMINI:
        return False, "Offline Mode."

    user_name = st.session_state.get("display_name", "you")

    prompt = f"""
    Act as a strict Code Reviewer.
    User Name: "{user_name}"

    1. Original Buggy Code:
    {original}

    2. User's Fix:
    {fix}

    3. Target Error to Fix: {predicted_error}

    4. SYNTAX CHECK: Passed (Valid Python)

    INSTRUCTIONS:
    - Since Syntax Passed: Do NOT complain about missing colons, parentheses, or indentation unless they break logic.
    - Focus ONLY on whether the logic fixes the '{predicted_error}'.
    - BUT if the code is valid and doesn't have the predicted_error, and the initial intent is unclear then let it pass
      as we can't be sure if it is correct or not.

    OUTPUT FORMAT:
    YES: [Encouraging remark]
    OR
    NO: [Specific hint. Do NOT give the answer code.]
    """

    try:
        res = generate_content_with_rotation(prompt)
        text = (res.text or "").strip()

        if text.upper().startswith("YES"):
            return True, text.split(":", 1)[1].strip() if ":" in text else "Good job!"
        return False, text.split(":", 1)[1].strip() if ":" in text else "Not quite."
    except Exception as e:
        return False, f"AI Error: {str(e)}"


def plot_skill_spider(skills_dict):
    if not skills_dict:
        return None

    max_score = max(skills_dict.values()) if skills_dict else 0
    graph_limit = max(10, max_score + 2)

    data = pd.DataFrame(dict(r=list(skills_dict.values()), theta=list(skills_dict.keys())))
    fig = px.line_polar(data, r='r', theta='theta', line_close=True)
    fig.update_traces(fill='toself')
    fig.update_layout(
        # Use the calculated limit here
        polar=dict(radialaxis=dict(visible=True, range=[0, graph_limit])),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white")
    )
    return fig


def sync_user_profile():
    """
    Function fetches skills, call get_player_profile, and update st.session_state.experience.
    """
    user_skills = database.get_user_skills(st.session_state.user_id)
    profile = get_player_profile(user_skills)
    st.session_state.experience = f"Lvl {profile['level']} | {profile['title']}"


# Page rendering functions
def render_auth_page():
    """
    The Login/Register forms and logic
    """
    st.markdown('<div class="card"><h2>🦉 Login to Socratic Tutor</h2></div>', unsafe_allow_html=True)

    mode = st.radio("Select Mode:", ["Login", "Register"],
                    horizontal=True,
                    key="auth_mode_select",
                    on_change=clear_auth_fields)

    st.write("")

    if mode == "Login":
        with st.form("login_form"):
            u = st.text_input("Username", key="auth_username")
            p = st.text_input("Password", type="password", key="auth_password")
            if st.form_submit_button("✨ Login", type="primary"):
                user = database.login_user(u, p)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user["id"]
                    st.session_state.username = user["username"]
                    st.session_state.display_name = user["display_name"]

                    if check_calibration_needed(user["id"]):
                        st.session_state.step = "calibration"
                    else:
                        st.session_state.step = "dashboard"

                    st.toast(f"Welcome back, {user['display_name']}!", icon="🦉")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")

    elif mode == "Register":
        with st.form("reg_form"):
            st.caption("Create a new account")
            nu = st.text_input("New Username", key="reg_username")
            np = st.text_input("New Password", type="password", key="reg_password")
            nd = st.text_input("Display Name", key="reg_display")

            if st.form_submit_button("Create Account", type="primary"):
                if nu and np:
                    success, msg = database.register_user(nu, np, nd)
                    if success:
                        st.success("✅ Account created! Logging in...")
                        user = database.login_user(nu, np)
                        st.session_state.logged_in = True
                        st.session_state.user_id = user["id"]
                        st.session_state.username = user["username"]
                        st.session_state.display_name = user["display_name"]
                        st.session_state.step = "calibration"
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
                else:
                    st.warning("All fields required.")
    st.stop()


def render_calibration_page():
    top_header()

    with st.sidebar:
        st.write("---")
        if st.button("⏩ Skip Calibration"):
            database.update_user_skills(st.session_state.user_id, {"Syntax": 1.0, "Logic": 1.0})
            st.session_state.step = "dashboard"
            st.rerun()

    if st.session_state.calib_idx >= len(CALIBRATION_TEST):
        database.update_user_skills(st.session_state.user_id, st.session_state.calib_score)
        st.balloons()

        st.markdown(
            '<div class="card"><h1>🎉 Calibration Complete!</h1><p>Here is your personalized skill profile:</p>',
            unsafe_allow_html=True)
        if not st.session_state.calib_score or sum(st.session_state.calib_score.values()) == 0:
            st.info("No skills recorded. Ready to start fresh!")
        else:
            fig = plot_skill_spider(st.session_state.calib_score)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("Enter Dashboard", type="primary"):
            st.session_state.step = "dashboard"
            st.rerun()
        st.stop()

    q = CALIBRATION_TEST[st.session_state.calib_idx]

    st.markdown(
        f'<div class="card"><h2>🎯 Calibration ({st.session_state.calib_idx + 1}/{len(CALIBRATION_TEST)})</h2>',
        unsafe_allow_html=True)

    max_lives = 3
    lives_left = max_lives - st.session_state.calib_attempts
    hearts = "❤️ " * lives_left + "💔 " * st.session_state.calib_attempts
    st.markdown(f'<div class="lives-container">Lives: {hearts}</div>', unsafe_allow_html=True)

    st.markdown(f'<h3>Topic: {q["topic"]}</h3>', unsafe_allow_html=True)
    st.code(q["code"], language="python")

    user_fix = st.text_area("Fix the code:", height=150, key=f"calib_input_{st.session_state.calib_idx}")

    c1, c2, c3 = st.columns([1, 1, 2])

    if st.session_state.calib_feedback:
        if st.session_state.calib_feedback_type == "success":
            st.success(st.session_state.calib_feedback)
        else:
            st.error(st.session_state.calib_feedback)

    if st.session_state.calib_status == "active":
        with c1:
            if st.button("Check Answer", type="primary"):
                with st.spinner("Analyzing..."):
                    passed, msg = ai_judge(q["code"], user_fix, q["topic"])

                    if passed:
                        st.session_state.calib_status = "success"
                        multiplier = max(0.5, 1.0 - (st.session_state.calib_attempts * 0.25))
                        points = {k: v * multiplier for k, v in q["reward"].items()}
                        for k, v in points.items():
                            st.session_state.calib_score[k] = st.session_state.calib_score.get(k, 0) + v
                        st.session_state.calib_feedback = f"✅ Correct! (Earned {int(multiplier * 100)}% points)"
                        st.session_state.calib_feedback_type = "success"
                    else:
                        st.session_state.calib_attempts += 1
                        if st.session_state.calib_attempts >= 3:
                            st.session_state.calib_status = "failed"
                            st.session_state.calib_feedback = f"❌ Incorrect. No lives left. Hint: {q['hint']}"
                            st.session_state.calib_feedback_type = "error"
                        else:
                            st.session_state.calib_feedback = f"❌ Incorrect. Try again. Hint: {q['hint']}"
                            st.session_state.calib_feedback_type = "error"
                    st.rerun()

    is_last_question = (st.session_state.calib_idx == len(CALIBRATION_TEST) - 1)
    btn_label = "Finish Calibration" if is_last_question else "Next Question →"

    if st.session_state.calib_status in ["success", "failed"]:
        with c1:
            if st.button(btn_label):
                st.session_state.calib_idx += 1
                st.session_state.calib_attempts = 0
                st.session_state.calib_status = "active"
                st.session_state.calib_feedback = None
                st.rerun()

    elif st.session_state.calib_status == "active":
        with c2:
            if st.button("Skip Question"):
                st.session_state.calib_idx += 1
                st.session_state.calib_attempts = 0
                st.session_state.calib_status = "active"
                st.session_state.calib_feedback = None
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


def render_dashboard():
    render_sidebar()

    skills = database.get_user_skills(st.session_state.user_id)
    stats = database.get_user_stats(st.session_state.user_id)
    user_sessions = database.get_user_sessions(st.session_state.user_id)
    weak_topic = analytics.recommend_study_topic(st.session_state.user_id)

    profile = get_player_profile(skills)

    # Update sidebar
    st.session_state.experience = f"Lvl {profile['level']} | {profile['title']}"

    # Display level & title
    st.markdown(f"### 🛡️ **Level {profile['level']}** — *{profile['title']}*")
    st.caption(f"Total XP: {profile['total_xp']}")

    # Top stats
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Solved", stats["success"])
    with c2:
        rate = int((stats['success'] / (stats['total'] or 1)) * 100)
        st.metric("Success Rate", f"{rate}%")
    with c3:
        if weak_topic:
            st.info(f"💡 Weakest Skill: **{weak_topic}**")
            if st.button(f"🏋️ Practice {weak_topic}", key="train_btn"):
                st.session_state.training_topic = weak_topic
                st.session_state.step = "training_selection"
                st.rerun()

    # Progress graph section
    st.markdown("### 📈 Learning Progress")
    prog_fig = analytics.generate_progress_chart(st.session_state.user_id)
    if prog_fig:
        st.plotly_chart(prog_fig, use_container_width=True)
    else:
        st.caption("Complete more sessions to see your progress graph!")

    st.markdown("---")

    col_left, col_right = st.columns([1, 1.5])

    with col_left:
        st.markdown('<div class="card"><h3>🧠 Skill Profile</h3>', unsafe_allow_html=True)
        if skills and sum(skills.values()) > 0:
            fig = plot_skill_spider(skills)
            st.plotly_chart(fig, use_container_width=True)

            # Next Rank Advice
            best_skill = max(skills, key=skills.get)
            current_val = skills[best_skill]
            next_goal = 5 if current_val < 5 else (10 if current_val < 10 else 20)

            if current_val < 20:
                st.info(f"💡 Tip: Reach **{next_goal}.0** in **{best_skill}** to rank up!")
            else:
                st.success(f"🌟 You are a {best_skill} Master!")
        else:
            st.caption("Solve problems to update your graph.")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("### 🚀 Actions")

        # Return to analysis button
        if st.session_state.get("current_session_id"):
            if st.button("⬅️ Return to Analysis", type="secondary", use_container_width=True):
                st.session_state.step = 3
                st.rerun()

        if st.button("➕ Start New Analysis", type="primary", use_container_width=True):
            st.session_state.user_code = ""
            st.session_state.current_session_id = str(uuid.uuid4())
            st.session_state.chat = []
            st.session_state.step = 1
            st.rerun()

    with col_right:
        st.markdown('<div class="card"><h3>📂 My Sessions</h3>', unsafe_allow_html=True)
        if user_sessions:
            for s in user_sessions:
                with st.expander(
                        f"{s['status']} | {s['timestamp'].strftime('%b %d %H:%M')} | {s['attempts_count']} tries"):
                    st.caption(f"Session ID: {s['session_id']}")

                    # Calculate & Display session gains
                    hist = database.get_session_history(s['session_id'])
                    session_gains = {}

                    for h in hist:
                        if h.get('rewards'):
                            for k, v in h['rewards'].items():
                                session_gains[k] = session_gains.get(k, 0) + v

                    if session_gains:
                        gains_str = ", ".join([f"+{v} {k}" for k, v in session_gains.items()])
                        st.success(f"📈 Gained: {gains_str}")

                    st.code(s['initial_code'], language="python")

                    for h in hist:
                        icon = "✅" if h['success'] else "❌"
                        st.text(f"{icon} {h['time']} - {h['code'][:30]}...")

                    if "Unsolved" in s['status']:
                        if st.button("↩️ Resume Session", key=f"btn_{s['session_id']}"):
                            last_code = hist[-1]['code'] if hist else s['initial_code']
                            st.session_state.user_code = last_code
                            st.session_state.current_session_id = s['session_id']
                            st.session_state.step = 3
                            st.rerun()
        else:
            st.info("No sessions yet.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()


def render_training_page():
    render_sidebar()

    topic = st.session_state.get("training_topic", "General")
    st.title(f"🏋️ Training: {topic}")
    st.caption("Select a problem to practice.")

    # Fetch questions
    if "training_pool" not in st.session_state or st.session_state.get("last_topic") != topic:
        user_skills = database.get_user_skills(st.session_state.user_id)

        all_snippets = []
        for k, v in retriever.by_error_type.items(): all_snippets.extend(v)

        candidates = [
            s for s in all_snippets
            if (topic in s.get('topic', '')
                or topic in s.get('error_type', '')
                or (topic in s.get('skill_rewards', {}) and s['skill_rewards'][topic] > 0)
            )
        ]

        # Fallback if user is locked out of everything in this topic
        if not candidates:
            st.warning(f"No unlocked problems found for {topic}. Showing General Novice problems.")
            candidates = [s for s in all_snippets if s.get('difficulty') == 'Novice'][:5]

        # Store fixed pool
        st.session_state.training_pool = random.sample(candidates, min(3, len(candidates)))
        st.session_state.last_topic = topic

    # Display options
    col1, col2, col3 = st.columns(3)
    user_skills = database.get_user_skills(st.session_state.user_id)

    for i, snippet in enumerate(st.session_state.training_pool):
        col_idx = i % 3
        with [col1, col2, col3][col_idx]:
            with st.container(height=250):
                st.markdown(f"**Problem {i + 1}**")
                st.code(snippet['code'], language="python")

                is_locked = is_problem_locked(snippet, user_skills)
                lock_msg = f"{snippet.get('difficulty')} Level"

                st.caption(f"Diff: {snippet.get('difficulty', 'Novice')}")
                st.write("")

            if is_locked:
                # Soft lock - show warning but allow click
                if st.button(f"⚠️ {lock_msg} (Try anyway)", key=f"train_{i}", type="secondary",
                             use_container_width=True):
                    st.session_state.analysis = {
                        "status": "success",
                        "top_match": snippet,
                        "warmup_candidates": [snippet],
                        "detected_concept": topic,
                        "confidence": 1.0
                    }
                    st.session_state.user_code = snippet['code']
                    st.session_state.current_session_id = str(uuid.uuid4())
                    st.session_state.chat = []
                    st.session_state.is_training_mode = True
                    st.session_state.step = 3
                    st.rerun()
            else:
                # Standard unlocked button
                if st.button(f"🚀 Solve #{i + 1}", key=f"train_{i}", type="primary", use_container_width=True):
                    st.session_state.analysis = {
                        "status": "success",
                        "top_match": snippet,
                        "warmup_candidates": [snippet],
                        "detected_concept": topic,
                        "confidence": 1.0
                    }
                    st.session_state.user_code = snippet['code']
                    st.session_state.current_session_id = str(uuid.uuid4())
                    st.session_state.chat = []
                    st.session_state.is_training_mode = True
                    st.session_state.step = 3
                    st.rerun()

    if st.button("⬅️ Back to Dashboard"):
        st.session_state.step = "dashboard"
        st.rerun()
    st.stop()


def render_step1_analyze():
    render_sidebar()
    st.title("Step 1: Analyze Code")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.caption("Paste your buggy Python code below.")

    code = st.text_area(
        "Paste Buggy Code",
        height=220,
        value=st.session_state.get("user_code", ""),
        placeholder="def func()\n  print('hello')"
    )
    st.markdown("</div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        if st.button("Analyze", type="primary"):
            st.session_state.user_code = code
            if not st.session_state.get("current_session_id"):
                st.session_state.current_session_id = str(uuid.uuid4())

            database.log_attempt(
                st.session_state.user_id, "USER_INPUT", code, False, st.session_state.current_session_id
            )

            with st.spinner("Analyzing..."):
                search_query = code
                syntax_error_msg = None

                try:
                    ast.parse(code)
                except SyntaxError as e:
                    syntax_error_msg = f"Syntax Error: {e.msg}"
                    search_query = f"{e.msg} syntax error python"

                result = retriever.find_similar(search_query)

                if syntax_error_msg:
                    if "top_match" not in result: result["top_match"] = {}
                    result["top_match"]["error_type"] = syntax_error_msg
                    result["detected_concept"] = "Syntax"

                # Filter warm-ups
                u_skills = database.get_user_skills(st.session_state.user_id)
                raw_candidates = result.get("warmup_candidates", [])
                valid_candidates = [s for s in raw_candidates if not is_problem_locked(s, u_skills)]

                if not valid_candidates and raw_candidates:
                    fallback_topic = raw_candidates[0].get('topic', 'General')
                    all_snips = []
                    for v in retriever.by_error_type.values(): all_snips.extend(v)
                    valid_candidates = [s for s in all_snips if
                                        s.get('difficulty') == 'Novice' and s.get('topic') == fallback_topic][:3]

                result["warmup_candidates"] = valid_candidates
                st.session_state.analysis = result
                st.session_state.match_index = random.randint(0, len(valid_candidates) - 1) if valid_candidates else 0
                st.session_state.step = 2
                st.rerun()

    with c3:
        st.info("Tip: Ask the tutor about ONE line you’re unsure about.")


def render_step2_warmup():
    render_sidebar()
    if st.button("⬅️ Dashboard"):
        st.session_state.step = "dashboard"
        st.rerun()

    analysis = st.session_state.analysis
    if analysis.get("status") == "low_confidence":
        candidates = []
        detected = "General Logic"
        st.warning("⚠️ Code pattern not found in database.")
    else:
        candidates = analysis.get("warmup_candidates", [])
        detected = analysis["detected_concept"].replace("Root", "Logic")

    if not candidates:
        match = {"code": "# No similar example found.\n# Try checking for Typos or Indentation.",
                 "hint": "Check syntax.", "error_type": "Unknown"}
    else:
        idx = st.session_state.match_index % len(candidates)
        match = candidates[idx]

    st.title("Step 2: Warm-up")
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Practice Example")
        st.caption(f"Topic: {detected}")
        st.code(match.get("code", ""), language="python")
        st.info(f"**Hint:** {match.get('hint', '')}")
        st.markdown("---")

        a, b = st.columns(2)
        with a:
            if len(candidates) > 1:
                if st.button("🔄 Different Example"):
                    st.session_state.match_index += 1
                    st.rerun()
            else:
                st.button("🔄 Different Example", disabled=True, help="No other examples available.")
        with b:
            if st.button("✅ I understand → Fix mine", type="primary"):
                st.session_state.chat = []
                st.session_state.step = 3
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Chat Tutor")

        chat_cont = st.container(height=420)
        with chat_cont:
            for m in st.session_state.chat:
                with st.chat_message(m["role"]): st.write(m["content"])

        if prompt := st.chat_input("Ask about this example..."):
            st.session_state.chat.append({"role": "user", "content": prompt})
            with chat_cont:
                with st.chat_message("user"): st.write(prompt)

            resp = get_tutor_response(st.session_state.chat, match.get("code", ""),
                                      {"phase": "Warmup", "concept": detected})
            st.session_state.chat.append({"role": "assistant", "content": resp})
            with chat_cont:
                with st.chat_message("assistant"): st.write(resp)

        st.markdown("</div>", unsafe_allow_html=True)


def render_step3_fix():
    render_sidebar()
    if st.button("⬅️ Dashboard"):
        st.session_state.step = "dashboard"
        st.rerun()

    st.title("Step 3: Fix Your Code")

    col1, col2 = st.columns([1, 1])
    submit_clicked = False

    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        new_code = st.text_area("Editor", value=st.session_state.user_code, height=420)

        b_cols = st.columns([1, 1, 2])
        with b_cols[0]:
            if st.button("Submit Fix", type="primary", use_container_width=True):
                submit_clicked = True

        if not st.session_state.get("is_training_mode", False):
            with b_cols[1]:
                if st.button("Back to Warm-up", use_container_width=True):
                    st.session_state.step = 2
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Chat Tutor")
        chat_cont = st.container(height=420)
        with chat_cont:
            for m in st.session_state.chat:
                with st.chat_message(m["role"]):
                    st.write(m["content"])

        if prompt := st.chat_input("Ask for help..."):
            st.session_state.chat.append({"role": "user", "content": prompt})
            with chat_cont:
                with st.chat_message("user"):
                    st.write(prompt)
            resp = get_tutor_response(st.session_state.chat, new_code, {"phase": "Fixing"})
            st.session_state.chat.append({"role": "assistant", "content": resp})
            with chat_cont:
                with st.chat_message("assistant"):
                    st.write(resp)
        st.markdown("</div>", unsafe_allow_html=True)

    if submit_clicked:
        with st.spinner("AI Judge is verifying..."):
            top_error = "Unknown"
            if st.session_state.analysis and "top_match" in st.session_state.analysis:
                top_error = st.session_state.analysis["top_match"]["error_type"]

            passed, reason = ai_judge(st.session_state.user_code, new_code, top_error)

            rewards_to_log = {}
            if passed:
                top_match = None
                if st.session_state.analysis:
                    top_match = st.session_state.analysis.get("top_match")

                if top_match and "skill_rewards" in top_match and top_match["skill_rewards"]:
                    rewards_to_log = top_match["skill_rewards"]
                else:
                    # Fallback heuristic
                    detected = st.session_state.analysis.get("detected_concept",
                                                             "") if st.session_state.analysis else "Logic"
                    rewards_to_log = {"Logic": 0.5}
                    if "Loop" in detected: rewards_to_log["Loops"] = 1.0
                    if "Recursion" in detected: rewards_to_log["Recursion"] = 1.5
                    if "Syntax" in detected or "Indentation" in detected: rewards_to_log["Syntax"] = 1.0
                    if "Data" in detected or "List" in detected: rewards_to_log["Data_Structures"] = 1.0

            database.log_attempt(
                st.session_state.user_id,
                "USER_INPUT",
                new_code,
                passed,
                st.session_state.get("current_session_id"),
                rewards=rewards_to_log
            )

        if passed:
            st.balloons()
            st.success(f"✅ {reason}")

            curr = database.get_user_skills(st.session_state.user_id)
            new_skills = {k: curr.get(k, 0) + rewards_to_log.get(k, 0) for k in curr}
            database.update_user_skills(st.session_state.user_id, new_skills)
        else:
            st.error(f"❌ {reason}")

            st.session_state.chat.append({"role": "assistant", "content": reason})
