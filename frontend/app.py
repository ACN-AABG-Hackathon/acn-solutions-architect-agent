import streamlit as st

st.set_page_config(page_title="Prompt Squad", page_icon="🚀")

st.title("🚀 Prompt Squad")
st.write("Welcome to the **Prompt Squad** web app — your portal for secure file uploads.")

st.sidebar.success("Select a page above to get started.")
COGNITO_DOMAIN = "https://qitbxlp6m.auth.us-east-1.amazoncognito.com" 
CLIENT_ID = st.secrets["APP_CLIENT_ID"]
REDIRECT_URI = "https://acn-solutions-architect-agent-webapp.streamlit.app/upload"
TOKEN_URL = f"{COGNITO_DOMAIN}/oauth2/token"

# Cognito login URL (replace with your actual Cognito Hosted UI URL)
#cognito_login_url = "https://us-east-1qitbxlp6m.auth.us-east-1.amazoncognito.com/login/continue?client_id=45hcn8a97al4j4hmmdhgsgvtvf&redirect_uri=https%3A%2F%2Facn-solutions-architect-agent-webapp.streamlit.app%2Fupload&response_type=code&scope=email+openid+phone"

cognito_login_url = (
    f"{COGNITO_DOMAIN}/login?"
    f"client_id={CLIENT_ID}"
    f"&response_type=code"
    f"&scope=email+openid+profile"
    f"&redirect_uri={REDIRECT_URI}"
)

if st.button("Login with Cognito"):
    st.write(f"Click [here to login]({cognito_login_url})")  # Provides a clickable link
    # Or automatically redirect in the browser using HTML
    st.markdown(f'<meta http-equiv="refresh" content="0; url={cognito_login_url}">', unsafe_allow_html=True)
