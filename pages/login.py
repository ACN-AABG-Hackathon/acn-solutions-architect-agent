import streamlit as st
import boto3

st.set_page_config(page_title="Prompt Squad Login", page_icon="🔐")

st.title("🔐 Prompt Squad Login")
st.caption("Sign in via Amazon Cognito")

AWS_REGION = "us-east-1"  # change to your region
USER_POOL_ID = "your_user_pool_id"
CLIENT_ID = "your_app_client_id"

username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Login"):
    client = boto3.client("cognito-idp", region_name=AWS_REGION)
    try:
        response = client.initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
            ClientId=CLIENT_ID
        )
        token = response["AuthenticationResult"]["AccessToken"]
        st.session_state["logged_in"] = True
        st.session_state["access_token"] = token
        st.success("✅ Login successful! Go to the Upload page.")
    except client.exceptions.NotAuthorizedException:
        st.error("❌ Invalid username or password.")
    except Exception as e:
        st.error(f"⚠️ Error: {e}")
