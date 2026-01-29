import streamlit as st
import ui_logic


def main():
    # Global Setup
    st.set_page_config(page_title="Socratic Tutor", layout="wide", page_icon="🦉")
    ui_logic.inject_global_css()
    ui_logic.init_session()

    # Sidebar Brain Status
    st.sidebar.title("🦉 Dashboard")

    if ui_logic.HAS_GEMINI:
        st.sidebar.success(f"Brain: {ui_logic.MODEL_NAME}")
    else:
        st.sidebar.error("Brain: Offline")

    # User Sync
    if st.session_state.logged_in and st.session_state.user_id:
        ui_logic.sync_user_profile()

    # Routing Logic
    if not st.session_state.logged_in:
        ui_logic.render_auth_page()
    elif st.session_state.step == "calibration":
        ui_logic.render_calibration_page()
    else:
        ui_logic.top_header()

        if st.session_state.step == "dashboard":
            ui_logic.render_dashboard()

        elif st.session_state.step == "training_selection":
            ui_logic.render_training_page()

        elif st.session_state.step == 1:
            ui_logic.render_step1_analyze()

        elif st.session_state.step == 2:
            ui_logic.render_step2_warmup()

        elif st.session_state.step == 3:
            ui_logic.render_step3_fix()


if __name__ == "__main__":
    main()


