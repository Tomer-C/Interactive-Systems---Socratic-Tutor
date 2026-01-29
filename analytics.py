import database
import pandas as pd
import plotly.express as px


def recommend_study_topic(user_id):
    """
    Looks at the UserSkills profile and returns the lowest scoring topic.
    """
    skills = database.get_user_skills(user_id)
    if not skills:
        return None

    weakest_topic = min(skills, key=skills.get)
    return weakest_topic


def generate_progress_chart(user_id):
    """Generates a line chart of skill progression over sessions."""
    raw_data = database.get_user_progress_data(user_id)
    if not raw_data: return None

    # Reconstruct score history
    history = []
    current_scores = {"Loops": 0.0, "Recursion": 0.0, "Syntax": 0.0, "Logic": 0.0, "Data_Structures": 0.0}

    # Add initial state
    history.append({"Session": "Start", **current_scores.copy()})

    seen_sessions = {}
    session_counter = 0

    for entry in raw_data:
        sid = entry['session_id']
        if sid not in seen_sessions:
            session_counter += 1
            seen_sessions[sid] = f"S{session_counter}"

        # Accumulate scores
        for skill, points in entry['rewards'].items():
            if skill in current_scores:
                current_scores[skill] += points

        # Snapshot current state
        snapshot = current_scores.copy()
        snapshot["Session"] = seen_sessions[sid]
        history.append(snapshot)

    df = pd.DataFrame(history)
    df_melted = df.melt('Session', var_name='Skill', value_name='Score')

    fig = px.line(df_melted, x='Session', y='Score', color='Skill', markers=True)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
    return fig