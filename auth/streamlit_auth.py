"""
Streamlit Authentication UI Components
Provides login, registration, and password reset forms
"""

import streamlit as st
from typing import Optional
from .cognito_auth import CognitoAuth


class StreamlitAuth:
    """Streamlit authentication UI handler"""
    
    def __init__(self, cognito_auth: CognitoAuth):
        """
        Initialize Streamlit authentication
        
        Args:
            cognito_auth: CognitoAuth instance
        """
        self.cognito = cognito_auth
        
        # Initialize session state
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user_info' not in st.session_state:
            st.session_state.user_info = None
        if 'access_token' not in st.session_state:
            st.session_state.access_token = None
        if 'refresh_token' not in st.session_state:
            st.session_state.refresh_token = None
        if 'auth_mode' not in st.session_state:
            st.session_state.auth_mode = 'login'  # 'login', 'register', 'verify', 'forgot_password'
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return st.session_state.authenticated
    
    def get_user_info(self) -> Optional[dict]:
        """Get current user information"""
        return st.session_state.user_info
    
    def get_username(self) -> Optional[str]:
        """Get current username"""
        if st.session_state.user_info:
            return st.session_state.user_info.get('username')
        return None
    
    def get_email(self) -> Optional[str]:
        """Get current user email"""
        if st.session_state.user_info:
            return st.session_state.user_info.get('attributes', {}).get('email')
        return None
    
    def login_form(self):
        """Display login form"""
        st.markdown("### 🔐 Login")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if not username or not password:
                    st.error("Please enter both username and password")
                    return
                
                with st.spinner("Logging in..."):
                    success, tokens, message = self.cognito.sign_in(username, password)
                    
                    if success:
                        # Get user info
                        user_success, user_info, _ = self.cognito.get_user(tokens['access_token'])
                        
                        if user_success:
                            st.session_state.authenticated = True
                            st.session_state.user_info = user_info
                            st.session_state.access_token = tokens['access_token']
                            st.session_state.refresh_token = tokens.get('refresh_token')
                            st.success(message)
                            st.rerun()
                        else:
                            st.error("Failed to retrieve user information")
                    else:
                        st.error(message)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Create Account"):
                st.session_state.auth_mode = 'register'
                st.rerun()
        with col2:
            if st.button("Forgot Password?"):
                st.session_state.auth_mode = 'forgot_password'
                st.rerun()
    
    def register_form(self):
        """Display registration form"""
        st.markdown("### 📝 Create Account")
        
        with st.form("register_form"):
            username = st.text_input("Username")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            password_confirm = st.text_input("Confirm Password", type="password")
            submit = st.form_submit_button("Register")
            
            if submit:
                if not username or not email or not password:
                    st.error("Please fill in all fields")
                    return
                
                if password != password_confirm:
                    st.error("Passwords do not match")
                    return
                
                with st.spinner("Creating account..."):
                    success, message = self.cognito.sign_up(username, password, email)
                    
                    if success:
                        st.success(message)
                        st.session_state.auth_mode = 'verify'
                        st.session_state.pending_username = username
                        st.rerun()
                    else:
                        st.error(message)
        
        if st.button("← Back to Login"):
            st.session_state.auth_mode = 'login'
            st.rerun()
    
    def verify_form(self):
        """Display email verification form"""
        st.markdown("### ✉️ Verify Email")
        st.info("Please check your email for the verification code")
        
        username = st.session_state.get('pending_username', '')
        
        with st.form("verify_form"):
            verification_code = st.text_input("Verification Code")
            submit = st.form_submit_button("Verify")
            
            if submit:
                if not verification_code:
                    st.error("Please enter the verification code")
                    return
                
                with st.spinner("Verifying..."):
                    success, message = self.cognito.confirm_sign_up(username, verification_code)
                    
                    if success:
                        st.success(message)
                        st.session_state.auth_mode = 'login'
                        if 'pending_username' in st.session_state:
                            del st.session_state.pending_username
                        st.rerun()
                    else:
                        st.error(message)
        
        if st.button("← Back to Login"):
            st.session_state.auth_mode = 'login'
            if 'pending_username' in st.session_state:
                del st.session_state.pending_username
            st.rerun()
    
    def forgot_password_form(self):
        """Display forgot password form"""
        st.markdown("### 🔑 Reset Password")
        
        if 'reset_username' not in st.session_state:
            # Step 1: Request reset code
            with st.form("forgot_password_form"):
                username = st.text_input("Username")
                submit = st.form_submit_button("Send Reset Code")
                
                if submit:
                    if not username:
                        st.error("Please enter your username")
                        return
                    
                    with st.spinner("Sending reset code..."):
                        success, message = self.cognito.forgot_password(username)
                        
                        if success:
                            st.success(message)
                            st.session_state.reset_username = username
                            st.rerun()
                        else:
                            st.error(message)
        else:
            # Step 2: Confirm reset with code
            username = st.session_state.reset_username
            st.info(f"Reset code sent to {username}'s email")
            
            with st.form("confirm_reset_form"):
                code = st.text_input("Reset Code")
                new_password = st.text_input("New Password", type="password")
                confirm_password = st.text_input("Confirm New Password", type="password")
                submit = st.form_submit_button("Reset Password")
                
                if submit:
                    if not code or not new_password:
                        st.error("Please fill in all fields")
                        return
                    
                    if new_password != confirm_password:
                        st.error("Passwords do not match")
                        return
                    
                    with st.spinner("Resetting password..."):
                        success, message = self.cognito.confirm_forgot_password(
                            username, code, new_password
                        )
                        
                        if success:
                            st.success(message)
                            st.session_state.auth_mode = 'login'
                            del st.session_state.reset_username
                            st.rerun()
                        else:
                            st.error(message)
        
        if st.button("← Back to Login"):
            st.session_state.auth_mode = 'login'
            if 'reset_username' in st.session_state:
                del st.session_state.reset_username
            st.rerun()
    
    def logout(self):
        """Log out current user"""
        if st.session_state.access_token:
            self.cognito.sign_out(st.session_state.access_token)
        
        # Clear session state
        st.session_state.authenticated = False
        st.session_state.user_info = None
        st.session_state.access_token = None
        st.session_state.refresh_token = None
        st.session_state.auth_mode = 'login'
        
        st.success("Logged out successfully")
        st.rerun()
    
    def render_auth_page(self):
        """Render authentication page based on current mode"""
        if st.session_state.auth_mode == 'login':
            self.login_form()
        elif st.session_state.auth_mode == 'register':
            self.register_form()
        elif st.session_state.auth_mode == 'verify':
            self.verify_form()
        elif st.session_state.auth_mode == 'forgot_password':
            self.forgot_password_form()
    
    def render_user_info(self):
        """Render user info in sidebar"""
        if self.is_authenticated():
            username = self.get_username()
            email = self.get_email()
            
            st.sidebar.markdown("---")
            st.sidebar.markdown("### 👤 User Info")
            st.sidebar.write(f"**Username:** {username}")
            if email:
                st.sidebar.write(f"**Email:** {email}")
            
            if st.sidebar.button("🚪 Logout"):
                self.logout()
    
    def require_auth(self):
        """
        Decorator/guard to require authentication
        Returns True if authenticated, False otherwise
        """
        if not self.is_authenticated():
            st.warning("Please log in to access this application")
            self.render_auth_page()
            st.stop()
            return False
        return True

