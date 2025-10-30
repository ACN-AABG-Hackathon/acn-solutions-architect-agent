"""
AWS Cognito Authentication for Streamlit
Handles user login, registration, and session management
"""

import boto3
import hmac
import hashlib
import base64
from typing import Optional, Dict, Tuple
import streamlit as st
from botocore.exceptions import ClientError


class CognitoAuth:
    """AWS Cognito authentication handler"""
    
    def __init__(
        self,
        user_pool_id: str,
        client_id: str,
        client_secret: Optional[str] = None,
        region: str = "us-east-1"
    ):
        """
        Initialize Cognito authentication
        
        Args:
            user_pool_id: Cognito User Pool ID
            client_id: Cognito App Client ID
            client_secret: Cognito App Client Secret (optional)
            region: AWS region
        """
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.region = region
        
        self.client = boto3.client('cognito-idp', region_name=region)
    
    def _get_secret_hash(self, username: str) -> Optional[str]:
        """Generate secret hash for Cognito authentication"""
        if not self.client_secret:
            return None
        
        message = username + self.client_id
        dig = hmac.new(
            self.client_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return base64.b64encode(dig).decode()
    
    def sign_up(
        self,
        username: str,
        password: str,
        email: str,
        **attributes
    ) -> Tuple[bool, str]:
        """
        Register a new user
        
        Args:
            username: Username
            password: Password
            email: Email address
            **attributes: Additional user attributes
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            user_attributes = [
                {'Name': 'email', 'Value': email}
            ]
            
            # Add additional attributes
            for key, value in attributes.items():
                user_attributes.append({'Name': key, 'Value': str(value)})
            
            params = {
                'ClientId': self.client_id,
                'Username': username,
                'Password': password,
                'UserAttributes': user_attributes
            }
            
            if self.client_secret:
                params['SecretHash'] = self._get_secret_hash(username)
            
            response = self.client.sign_up(**params)
            
            return True, "Registration successful! Please check your email for verification code."
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'UsernameExistsException':
                return False, "Username already exists"
            elif error_code == 'InvalidPasswordException':
                return False, "Password does not meet requirements"
            elif error_code == 'InvalidParameterException':
                return False, f"Invalid parameter: {error_message}"
            else:
                return False, f"Registration failed: {error_message}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def confirm_sign_up(
        self,
        username: str,
        confirmation_code: str
    ) -> Tuple[bool, str]:
        """
        Confirm user registration with verification code
        
        Args:
            username: Username
            confirmation_code: Verification code from email
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            params = {
                'ClientId': self.client_id,
                'Username': username,
                'ConfirmationCode': confirmation_code
            }
            
            if self.client_secret:
                params['SecretHash'] = self._get_secret_hash(username)
            
            self.client.confirm_sign_up(**params)
            
            return True, "Email verified successfully! You can now log in."
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'CodeMismatchException':
                return False, "Invalid verification code"
            elif error_code == 'ExpiredCodeException':
                return False, "Verification code has expired"
            else:
                return False, f"Verification failed: {error_message}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def sign_in(
        self,
        username: str,
        password: str
    ) -> Tuple[bool, Optional[Dict], str]:
        """
        Authenticate user
        
        Args:
            username: Username
            password: Password
        
        Returns:
            Tuple of (success: bool, tokens: Dict, message: str)
        """
        try:
            params = {
                'AuthFlow': 'USER_PASSWORD_AUTH',
                'ClientId': self.client_id,
                'AuthParameters': {
                    'USERNAME': username,
                    'PASSWORD': password
                }
            }
            
            if self.client_secret:
                params['AuthParameters']['SECRET_HASH'] = self._get_secret_hash(username)
            
            response = self.client.initiate_auth(**params)
            
            # Extract tokens
            auth_result = response.get('AuthenticationResult', {})
            tokens = {
                'access_token': auth_result.get('AccessToken'),
                'id_token': auth_result.get('IdToken'),
                'refresh_token': auth_result.get('RefreshToken'),
                'token_type': auth_result.get('TokenType'),
                'expires_in': auth_result.get('ExpiresIn')
            }
            
            return True, tokens, "Login successful!"
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'NotAuthorizedException':
                return False, None, "Incorrect username or password"
            elif error_code == 'UserNotConfirmedException':
                return False, None, "Please verify your email first"
            elif error_code == 'UserNotFoundException':
                return False, None, "User not found"
            else:
                return False, None, f"Login failed: {error_message}"
        except Exception as e:
            return False, None, f"Unexpected error: {str(e)}"
    
    def get_user(self, access_token: str) -> Tuple[bool, Optional[Dict], str]:
        """
        Get user information from access token
        
        Args:
            access_token: Access token from sign_in
        
        Returns:
            Tuple of (success: bool, user_info: Dict, message: str)
        """
        try:
            response = self.client.get_user(AccessToken=access_token)
            
            # Parse user attributes
            user_info = {
                'username': response['Username'],
                'attributes': {}
            }
            
            for attr in response.get('UserAttributes', []):
                user_info['attributes'][attr['Name']] = attr['Value']
            
            return True, user_info, "User info retrieved"
            
        except ClientError as e:
            return False, None, f"Failed to get user info: {e.response['Error']['Message']}"
        except Exception as e:
            return False, None, f"Unexpected error: {str(e)}"
    
    def refresh_token(self, refresh_token: str, username: str) -> Tuple[bool, Optional[Dict], str]:
        """
        Refresh access token
        
        Args:
            refresh_token: Refresh token from sign_in
            username: Username
        
        Returns:
            Tuple of (success: bool, new_tokens: Dict, message: str)
        """
        try:
            params = {
                'AuthFlow': 'REFRESH_TOKEN_AUTH',
                'ClientId': self.client_id,
                'AuthParameters': {
                    'REFRESH_TOKEN': refresh_token
                }
            }
            
            if self.client_secret:
                params['AuthParameters']['SECRET_HASH'] = self._get_secret_hash(username)
            
            response = self.client.initiate_auth(**params)
            
            auth_result = response.get('AuthenticationResult', {})
            tokens = {
                'access_token': auth_result.get('AccessToken'),
                'id_token': auth_result.get('IdToken'),
                'token_type': auth_result.get('TokenType'),
                'expires_in': auth_result.get('ExpiresIn')
            }
            
            return True, tokens, "Token refreshed"
            
        except ClientError as e:
            return False, None, f"Token refresh failed: {e.response['Error']['Message']}"
        except Exception as e:
            return False, None, f"Unexpected error: {str(e)}"
    
    def sign_out(self, access_token: str) -> Tuple[bool, str]:
        """
        Sign out user (revoke token)
        
        Args:
            access_token: Access token from sign_in
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            self.client.global_sign_out(AccessToken=access_token)
            return True, "Signed out successfully"
        except ClientError as e:
            return False, f"Sign out failed: {e.response['Error']['Message']}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def forgot_password(self, username: str) -> Tuple[bool, str]:
        """
        Initiate password reset
        
        Args:
            username: Username
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            params = {
                'ClientId': self.client_id,
                'Username': username
            }
            
            if self.client_secret:
                params['SecretHash'] = self._get_secret_hash(username)
            
            self.client.forgot_password(**params)
            
            return True, "Password reset code sent to your email"
            
        except ClientError as e:
            return False, f"Password reset failed: {e.response['Error']['Message']}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def confirm_forgot_password(
        self,
        username: str,
        confirmation_code: str,
        new_password: str
    ) -> Tuple[bool, str]:
        """
        Confirm password reset with code
        
        Args:
            username: Username
            confirmation_code: Code from email
            new_password: New password
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            params = {
                'ClientId': self.client_id,
                'Username': username,
                'ConfirmationCode': confirmation_code,
                'Password': new_password
            }
            
            if self.client_secret:
                params['SecretHash'] = self._get_secret_hash(username)
            
            self.client.confirm_forgot_password(**params)
            
            return True, "Password reset successful! You can now log in."
            
        except ClientError as e:
            return False, f"Password reset failed: {e.response['Error']['Message']}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

