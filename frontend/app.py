import streamlit as st

st.set_page_config(page_title="Prompt Squad", page_icon="🚀")

st.title("🚀 Prompt Squad")
st.write("Welcome to the **Prompt Squad** web app — your portal for secure file uploads.")

st.sidebar.success("Select a page above to get started.")

# Cognito login URL (replace with your actual Cognito Hosted UI URL)
cognito_login_url = "https://us-east-1qitbxlp6m.auth.us-east-1.amazoncognito.com/login?client_id=45hcn8a97al4j4hmmdhgsgvtvf&response_type=code&scope=email+openid+phone&redirect_uri=https%3A%2F%2Facn-solutions-architect-agent-webapp.streamlit.app%2Fupload"

if st.button("Login with Cognito"):
    st.write(f"Click [here to login]({cognito_login_url})")  # Provides a clickable link
    # Or automatically redirect in the browser using HTML
    st.markdown(f'<meta http-equiv="refresh" content="0; url={cognito_login_url}">', unsafe_allow_html=True)
