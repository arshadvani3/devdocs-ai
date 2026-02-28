"""
Authentication Service for User Management
Handles user registration, login, and JWT token generation.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class User:
    """Represents a user in the system."""

    def __init__(self, user_id: int, username: str, email: str, password_hash: str):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.created_at = datetime.utcnow()
        self.last_login = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert user object to dictionary."""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class AuthService:
    """
    Authentication service handling user registration, login, and token management.
    Uses JWT tokens for stateless authentication with 24-hour expiry.
    """

    def __init__(self, secret_key: str):
        """
        Initialize authentication service.

        Args:
            secret_key: Secret key for JWT token signing
        """
        self.secret_key = secret_key
        self.users_db = {}  # In production, this would be a database
        self.token_expiry_hours = 24

    def hash_password(self, password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """
        Hash a password using SHA-256 with a random salt.

        Args:
            password: Plain text password to hash
            salt: Optional salt, generates new one if not provided

        Returns:
            Tuple of (password_hash, salt)
        """
        if salt is None:
            salt = secrets.token_hex(32)

        password_hash = hashlib.sha256(
            f"{password}{salt}".encode()
        ).hexdigest()

        return password_hash, salt

    def register_user(self, username: str, email: str, password: str) -> User:
        """
        Register a new user in the system.

        Args:
            username: Unique username
            email: User's email address
            password: Plain text password (will be hashed)

        Returns:
            Created User object

        Raises:
            ValueError: If username already exists
        """
        if username in self.users_db:
            raise ValueError(f"Username '{username}' already exists")

        # Hash the password with a unique salt
        password_hash, salt = self.hash_password(password)

        # Create new user
        user_id = len(self.users_db) + 1
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=f"{password_hash}:{salt}"
        )

        # Store user
        self.users_db[username] = user

        return user

    def authenticate_user(self, username: str, password: str) -> User:
        """
        Authenticate a user with username and password.

        Args:
            username: Username to authenticate
            password: Plain text password to verify

        Returns:
            Authenticated User object

        Raises:
            AuthenticationError: If credentials are invalid
        """
        # Check if user exists
        user = self.users_db.get(username)
        if not user:
            raise AuthenticationError("Invalid username or password")

        # Extract stored hash and salt
        stored_hash, salt = user.password_hash.split(':')

        # Hash provided password with stored salt
        provided_hash, _ = self.hash_password(password, salt)

        # Compare hashes
        if provided_hash != stored_hash:
            raise AuthenticationError("Invalid username or password")

        # Update last login time
        user.last_login = datetime.utcnow()

        return user

    def generate_token(self, user: User) -> str:
        """
        Generate a JWT token for authenticated user.

        Args:
            user: Authenticated user object

        Returns:
            JWT token string valid for 24 hours
        """
        expiry = datetime.utcnow() + timedelta(hours=self.token_expiry_hours)

        payload = {
            'user_id': user.user_id,
            'username': user.username,
            'email': user.email,
            'exp': expiry,
            'iat': datetime.utcnow()
        }

        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        return token

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string to verify

        Returns:
            Decoded token payload

        Raises:
            AuthenticationError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")

    def login(self, username: str, password: str) -> tuple[User, str]:
        """
        Complete login flow: authenticate user and generate token.

        Args:
            username: Username for login
            password: Password for login

        Returns:
            Tuple of (authenticated_user, jwt_token)

        Raises:
            AuthenticationError: If authentication fails
        """
        user = self.authenticate_user(username, password)
        token = self.generate_token(user)
        return user, token


# Example usage
if __name__ == "__main__":
    # Initialize service
    auth = AuthService(secret_key="super-secret-key-change-in-production")

    # Register a user
    user = auth.register_user(
        username="john_doe",
        email="john@example.com",
        password="SecurePass123!"
    )
    print(f"Registered user: {user.username}")

    # Login and get token
    authenticated_user, token = auth.login("john_doe", "SecurePass123!")
    print(f"Login successful! Token: {token[:50]}...")

    # Verify token
    payload = auth.verify_token(token)
    print(f"Token valid for user: {payload['username']}")
