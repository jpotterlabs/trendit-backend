"""
Auth0 Integration Service for Trendit

Handles Auth0 JWT verification and user management integration
"""

import os
import requests
from typing import Optional, Dict, Any
from jose import jwt, jwk
from jose.exceptions import JWTError, JWTClaimsError, ExpiredSignatureError
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from models.models import User, SubscriptionStatus
from passlib.context import CryptContext
import logging

logger = logging.getLogger(__name__)

class Auth0Service:
    def __init__(self):
        self.domain = os.getenv("AUTH0_DOMAIN")
        self.client_id = os.getenv("AUTH0_CLIENT_ID")
        self.client_secret = os.getenv("AUTH0_CLIENT_SECRET")
        self.audience = os.getenv("AUTH0_AUDIENCE")
        
        if not all([self.domain, self.client_id, self.audience]):
            raise ValueError("Missing Auth0 configuration. Check AUTH0_DOMAIN, AUTH0_CLIENT_ID, and AUTH0_AUDIENCE in .env")
        
        self.issuer = f"https://{self.domain}/"
        self.jwks_url = f"https://{self.domain}/.well-known/jwks.json"
        
        # Cache for JWKS
        self._jwks_cache = None
        
    def get_jwks(self) -> Dict[str, Any]:
        """Fetch and cache Auth0 JWKS (JSON Web Key Set)"""
        if self._jwks_cache is None:
            try:
                response = requests.get(self.jwks_url)
                response.raise_for_status()
                self._jwks_cache = response.json()
            except requests.RequestException as e:
                logger.error(f"Failed to fetch JWKS from Auth0: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Unable to verify authentication tokens"
                )
        return self._jwks_cache
    
    def get_signing_key(self, token_header: Dict[str, Any]) -> str:
        """Get the RSA key for JWT signature verification"""
        jwks = self.get_jwks()
        
        if "kid" not in token_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token header: missing key ID"
            )
        
        # Find the key with matching kid
        key = None
        for jwk_key in jwks.get("keys", []):
            if jwk_key.get("kid") == token_header["kid"]:
                key = jwk.construct(jwk_key).to_pem()
                break
        
        if key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate signing key"
            )
        
        return key
    
    def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """Verify Auth0 JWT token and return claims"""
        try:
            # Decode header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            
            # Get the signing key
            key = self.get_signing_key(unverified_header)
            
            # Verify and decode the token
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
            )
            
            return payload
            
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except JWTClaimsError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims"
            )
        except JWTError as e:
            logger.error(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to verify token"
            )
    
    def get_or_create_user(self, auth0_claims: Dict[str, Any], db: Session) -> User:
        """Get existing user or create new user from Auth0 claims"""
        
        # Extract user info from Auth0 claims
        auth0_user_id = auth0_claims.get("sub")  # Auth0 user ID
        email = auth0_claims.get("email")
        name = auth0_claims.get("name", "")
        picture = auth0_claims.get("picture")
        
        # Determine provider from sub (e.g., "google-oauth2|123" -> "google")
        provider = "auth0"  # default
        if auth0_user_id:
            if auth0_user_id.startswith("google-oauth2|"):
                provider = "google"
            elif auth0_user_id.startswith("github|"):
                provider = "github"
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required from Auth0 token"
            )
        
        # Check if user exists by email
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            # Update existing user with Auth0 info if not already set
            if not user.auth0_user_id:
                user.auth0_user_id = auth0_user_id
                user.auth0_provider = provider
                if picture and not hasattr(user, 'profile_picture'):
                    # Could add profile_picture field to User model later
                    pass
                db.commit()
            
            logger.info(f"Existing user logged in via Auth0: {email}")
            return user
        
        else:
            # Create new user
            # Generate username from name or email
            username = name.replace(" ", "_").lower() if name else email.split("@")[0]
            
            # Ensure username is unique
            base_username = username
            counter = 1
            while db.query(User).filter(User.username == username).first():
                username = f"{base_username}_{counter}"
                counter += 1
            
            new_user = User(
                email=email,
                username=username,
                password_hash="",  # No password for OAuth users
                is_active=True,
                subscription_status=SubscriptionStatus.INACTIVE,  # Default to free tier
                auth0_user_id=auth0_user_id,
                auth0_provider=provider
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            logger.info(f"New user created via Auth0: {email} ({provider})")
            return new_user
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user info from Auth0 using access token"""
        try:
            response = requests.get(
                f"https://{self.domain}/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get user info from Auth0: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to fetch user information"
            )


# Global instance
auth0_service = Auth0Service()