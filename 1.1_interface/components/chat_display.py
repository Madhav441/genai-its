import streamlit as st

def display_chat(user_input, response):
    st.markdown("### 🧑‍🎓 You")
    st.write(user_input)
    st.markdown("### 🤖 TutorBot")
    st.write(response)
