import streamlit as st

st.title("AI Health Companion")

user_input = st.text_input("How can I help you?")

if user_input:
    st.write("Processing...")
