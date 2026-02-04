import streamlit as st


LANGUAGE_OPTIONS = ["English", "Hindi", "Spanish", "French"]
TIMEZONE_OPTIONS = ["UTC", "Asia/Kolkata", "Europe/London", "America/New_York"]
PERSONALITY_OPTIONS = ["Cheeky", "Professional", "Friendly", "Supportive"]
AVATAR_OPTIONS = ["Neon 3D", "Soft Pastel", "Minimal Mono", "Cyber Punk"]
PLAN_OPTIONS = ["Free", "Pro", "Startup Tier"]
LLM_OPTIONS = ["OpenAI", "Gemini", "Local"]
STATUS_OPTIONS = ["Active", "Suspended", "Pending"]


def render_user_info():
    st.subheader("User Info")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("User ID", value="USR-1024")
        st.text_input("Display Name", value="Aarav")
        st.text_input("Email Address", value="aarav@example.com")
    with col2:
        st.selectbox("Language Preference", LANGUAGE_OPTIONS)
        st.selectbox("Timezone", TIMEZONE_OPTIONS)


def render_character_info():
    st.subheader("Character Info (Companion Customization)")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Companion Name", value="Chikki")
        st.selectbox("Personality Mode", PERSONALITY_OPTIONS)
        st.selectbox("Avatar Style", AVATAR_OPTIONS)
    with col2:
        st.select_slider("Interaction Level", options=["Low", "Medium", "High"])
        st.toggle("Mood Sensitivity", value=True)


def render_subscription_plan():
    st.subheader("Subscription & Plan")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.selectbox("Current Plan", PLAN_OPTIONS, index=1)
    with col2:
        st.number_input("Credit Balance", min_value=0, max_value=500, value=5)
    with col3:
        st.selectbox("Billing Cycle", ["Monthly", "Annual"])
    st.button("Upgrade / Renew", type="primary")


def render_api_customization():
    st.subheader("API & Customization")
    st.markdown("**API Configuration**")
    col1, col2 = st.columns(2)
    with col1:
        st.selectbox("LLM Provider", LLM_OPTIONS)
    with col2:
        st.text_input("User API Key", type="password")

    st.markdown("**Custom Prompt (System Instructions)**")
    st.text_area("Primary Directive", value="Always be funny and use emojis.")
    st.slider("Memory Window", min_value=1, max_value=50, value=12)


def render_user_dashboard():
    st.header("Part 1: User Dashboard (Settings Page)")
    with st.form("user_settings_form"):
        render_user_info()
        st.divider()
        render_character_info()
        st.divider()
        render_subscription_plan()
        st.divider()
        render_api_customization()
        st.form_submit_button("Save Settings")


def render_user_management():
    st.subheader("User Management (Edit/View)")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("User Search/Filter", placeholder="Search by User ID, Email, or Name")
        st.selectbox("Account Status", STATUS_OPTIONS)
    with col2:
        st.number_input("Manual Credit Adjustment", min_value=-100, max_value=100, value=0)
        st.button("Edit Profile")


def render_system_analysis():
    st.subheader("System Analysis & Items")
    st.markdown("**Global Analytics**")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Active Users", "1,284", "+3.2%")
    with col2:
        st.metric("API Usage Trends", "1.2M tokens/day", "+5%")
    with col3:
        st.metric("Most Popular Character Modes", "Friendly", "+12%")

    st.markdown("**Health Monitor**")
    col1, col2 = st.columns(2)
    with col1:
        st.success("Backend Status: FastAPI Uptime 99.98%")
    with col2:
        st.info("Database Latency: 180ms (p95)")

    st.markdown("**Feedback/Logs**")
    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(
            [
                {"Time": "2025-01-22 09:12", "Event": "Desktop app crash in audio driver"},
                {"Time": "2025-01-22 10:07", "Event": "Failed auth token refresh"},
            ],
            use_container_width=True,
            hide_index=True,
        )
    with col2:
        st.dataframe(
            [
                {"User": "USR-1024", "Feedback": "Please add more avatar skins."},
                {"User": "USR-2177", "Feedback": "Add daily summary emails to my inbox."},
            ],
            use_container_width=True,
            hide_index=True,
        )


def render_admin_dashboard():
    st.header("Part 2: Admin Dashboard (Management Page)")
    with st.form("admin_controls_form"):
        render_user_management()
        st.form_submit_button("Apply Filters")
    st.divider()
    render_system_analysis()


def render_implementation_note():
    with st.expander("Technical Implementation Note"):
        st.markdown(
            "Since you are using FastAPI for your backend (like in SkillSynth), "
            "group these into three main API endpoints:\n\n"
            "- **GET /api/v1/user/settings** — Returns the combined User, Character, and Plan info.\n"
            "- **PATCH /api/v1/user/update** — Updates the custom prompt or character info.\n"
            "- **GET /api/v1/admin/dashboard** — A protected route (Admin only) to fetch the global analysis."
        )


def main():
    st.set_page_config(page_title="Chikki Dashboard", layout="wide")
    st.title("Chikki Companion Dashboard")
    st.caption("Customize your companion experience and manage the platform.")

    with st.sidebar:
        st.subheader("Quick Actions")
        st.button("Sync Settings")
        st.button("Export Analytics")
        st.caption("Last sync: 2 mins ago")

    tabs = st.tabs(["User Dashboard", "Admin Dashboard"])
    with tabs[0]:
        render_user_dashboard()
    with tabs[1]:
        render_admin_dashboard()

    render_implementation_note()


if __name__ == "__main__":
    main()
