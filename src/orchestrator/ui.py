import streamlit as st
from orchestrator_agent.router import orchestrate_user_request
from orchestrator_agent.state_manager import load_state

st.set_page_config(page_title="Health Orchestrator", page_icon="🩺")
st.title("🩺 Multi-Agent Patient Health Companion")

state = load_state()

st.subheader("Patient Overview")
st.write(f"**Patient:** {state.get('patient')}")
st.write(f"**Conditions:** {', '.join(state.get('conditions', []))}")
st.write(f"**Symptoms today:** {', '.join(state.get('symptoms_today', [])) or 'None'}")

agent = st.selectbox(
    "Choose agent",
    [
        "symptoms",
        "diet",
        "medication",
        "appointment_previsit",
        "appointment_summary",
        "caregiver"
    ]
)

query = ""
if agent in ["symptoms", "diet"]:
    query = st.text_input("Enter your message")

if st.button("Run Agent"):
    result = orchestrate_user_request(agent, query)
    st.write(result)

if state.get("alerts"):
    st.subheader("Alerts")
    for alert in state["alerts"][-5:]:
        st.write(alert)
