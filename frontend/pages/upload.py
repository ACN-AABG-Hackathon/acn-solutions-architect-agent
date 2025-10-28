import streamlit as st
import boto3
from botocore.exceptions import NoCredentialsError
import requests

st.set_page_config(page_title="Prompt Squad Uploader", page_icon="🚀")

st.title("🚀 Prompt Squad Document Uploader")
st.subheader("Direct upload to S3")

# ----------------------
# Cognito login setup
# ----------------------
COGNITO_DOMAIN = "us-east-1qitbxlp6m.auth.us-east-1.amazoncognito.com"
CLIENT_ID =  st.secrets["APP_CLIENT_ID"]
REDIRECT_URI = "https://acn-solutions-architect-agent-webapp.streamlit.app/upload"
TOKEN_URL = f"https://{COGNITO_DOMAIN}/oauth2/token"

#LOGIN_URL = (
#    f"https://{COGNITO_DOMAIN}/login?client_id={CLIENT_ID}"
#    f"&response_type=code&scope=email+openid&redirect_uri={REDIRECT_URI}"
#)

LOGIN_URL = f"https://us-east-1qitbxlp6m.auth.us-east-1.amazoncognito.com/login/continue?client_id={CLIENT_ID}&redirect_uri=https%3A%2F%2Facn-solutions-architect-agent-webapp.streamlit.app%2Fupload&response_type=code&scope=email+openid+phone)%22%3E%27"

st.toast("initialize session_state")
# Initialize session state for login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "id_token" not in st.session_state:
    st.session_state.id_token = None

# Check if Cognito redirected back with a code
code = st.experimental_get_query_params().get("code")
st.toast("check session_state")
if code and not st.session_state.logged_in:
    st.toast("not logged in")
    code = code[0]  # Get the actual code string
    # Exchange code for tokens
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        response = requests.post(TOKEN_URL, data=data, headers=headers)
        response.raise_for_status()
        tokens = response.json()
        st.session_state.logged_in = True
        st.session_state.id_token = tokens["id_token"]
        st.success("✅ Logged in successfully via Cognito!")
    except Exception as e:
        st.error(f"❌ Login failed: {e}")

# Show login button if not logged in
st.toast("not logged in") 
if not st.session_state.logged_in:
    st.warning("Please log in with Cognito to upload files.")
    if st.button("Login with Cognito"):
        st.markdown(f'<meta http-equiv="refresh" content="0; url={LOGIN_URL}">', unsafe_allow_html=True)
    st.stop()  # Stop the rest of the app until login

# ----------------------
# AWS S3 upload
# ----------------------
AWS_ACCESS_KEY = st.secrets["AWS_ACCESS_KEY_ID"]
AWS_SECRET_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
AWS_REGION = "us-east-1"   # change if needed
BUCKET_NAME = "aws-architect-agent-requirement"

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

uploaded_file = st.file_uploader("Upload PDF, DOCX, or TXT file", type=["pdf", "docx", "txt"])

if uploaded_file is not None:
    st.info(f"📁 Selected: {uploaded_file.name}")
    if st.button("Upload to S3"):
        try:
            s3.upload_fileobj(uploaded_file, BUCKET_NAME, f"documents/{uploaded_file.name}")
            st.success("✅ File uploaded successfully to S3!")
        except NoCredentialsError:
            st.error("❌ AWS credentials not found.")
        except Exception as e:
            st.error(f"❌ Upload failed: {e}")

st.markdown("---")
