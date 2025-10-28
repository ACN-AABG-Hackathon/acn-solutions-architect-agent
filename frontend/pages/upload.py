import streamlit as st
import boto3
from botocore.exceptions import NoCredentialsError
import requests
from requests.auth import HTTPBasicAuth
import urllib.parse

st.set_page_config(page_title="Prompt Squad Uploader", page_icon="🚀")
st.title("🚀 Prompt Squad Document Uploader")
st.subheader("Direct upload to S3")

# ----------------------
# Cognito login setup
# ----------------------
COGNITO_DOMAIN = "https://us-east-1qitbxlp6m.auth.us-east-1.amazoncognito.com"
CLIENT_ID = st.secrets["APP_CLIENT_ID"]
CLIENT_SECRET = st.secrets["APP_CLIENT_SECRET"]
REDIRECT_URI = "https://acn-solutions-architect-agent-webapp.streamlit.app/upload"
LOGOUT_URI = "https://acn-solutions-architect-agent-webapp.streamlit.app/"
TOKEN_URL = f"{COGNITO_DOMAIN}/oauth2/token"
LOGIN_URL = (
    f"{COGNITO_DOMAIN}/login/continue?client_id={CLIENT_ID}"
    f"&response_type=code&scope=email+openid&redirect_uri={REDIRECT_URI}"
)
LOGOUT_URL = (
        f"{COGNITO_DOMAIN}/logout?"
        f"client_id={CLIENT_ID}&"
        f"logout_uri={urllib.parse.quote(LOGOUT_URI)}"
)


# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "id_token" not in st.session_state:
    st.session_state.id_token = None

# Check if Cognito redirected back with a code
code = st.experimental_get_query_params().get("code")
if code and not st.session_state.logged_in:
    code = code[0]
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        response = requests.post(
            TOKEN_URL,
            data=data,
            headers=headers,
            auth=HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
        )
        response.raise_for_status()
        tokens = response.json()
        st.session_state.logged_in = True
        st.session_state.id_token = tokens["id_token"]
        st.success("✅ Logged in successfully via Cognito!")
    except Exception as e:
        st.error(f"❌ Login failed: {e}")

# Show login button if not logged in
if not st.session_state.logged_in:
    st.warning("Please log in with Cognito to upload files.")
    st.markdown(f"[Login to Cognito]({LOGIN_URL})", unsafe_allow_html=True)
    st.stop()
# ----------------------
# Cognito logout setup
# ----------------------
def logout_user(): 
    #Clear local session
    for key in list(st.session_state.keys()):
        del st.session_state[key]    

    #Redirect to Cognito Logout 
    st.write(f'<meta http-equiv="refresh" content="0; url={LOGOUT_URL}">', unsafe_allow_html=True)

    #Check if user is logged in 
    if "username" in st.session_state: 
        st.write(f"👋 Hello, {st.session_state['username']}!")
        if st.button("Logout"): 
            logout_user()
        else: 
            st.write("You are not logged in")
# ----------------------
# AWS S3 upload
# ----------------------
AWS_ACCESS_KEY = st.secrets["AWS_ACCESS_KEY_ID"]
AWS_SECRET_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
AWS_REGION = "us-east-1"
BUCKET_NAME = "aws-architect-agent-requirement"

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

uploaded_file = st.file_uploader("Upload PDF, DOCX, or TXT file", type=["pdf", "docx", "txt"])
if uploaded_file:
    st.info(f"📁 Selected: {uploaded_file.name}")
    if st.button("Upload to S3"):
        try:
            s3.upload_fileobj(uploaded_file, BUCKET_NAME, f"documents/{uploaded_file.name}")
            st.success("✅ File uploaded successfully to S3!")
        except NoCredentialsError:
            st.error("❌ AWS credentials not found.")
        except Exception as e:
            st.error(f"❌ Upload failed: {e}")
