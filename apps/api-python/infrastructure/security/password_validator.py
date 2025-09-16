"""Password strength validation and security utilities"""

import re
import string
import secrets
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class PasswordStrength(Enum):
    """Password strength levels"""
    VERY_WEAK = 1
    WEAK = 2
    FAIR = 3
    GOOD = 4
    STRONG = 5


@dataclass
class PasswordValidationResult:
    """Result of password validation"""
    is_valid: bool
    strength: PasswordStrength
    score: int
    feedback: List[str]
    suggestions: List[str]


class PasswordValidator:
    """Advanced password validation and strength checking"""
    
    def __init__(self):
        # Common passwords list (top 1000 most common)
        self.common_passwords = self._load_common_passwords()
        
        # Keyboard patterns
        self.keyboard_patterns = [
            "qwerty", "asdf", "zxcv", "123456", "abcdef",
            "qwertyuiop", "asdfghjkl", "zxcvbnm",
            "1234567890", "0987654321"
        ]
        
        # Personal info patterns that should be avoided
        self.personal_patterns = [
            r"password", r"admin", r"user", r"login", r"account",
            r"company", r"trading", r"exchange", r"crypto", r"bitcoin"
        ]
    
    def validate_password(self, password: str, user_info: Optional[Dict] = None) -> PasswordValidationResult:
        """
        Comprehensive password validation
        
        Args:
            password: Password to validate
            user_info: Optional user information to check against (email, name, etc.)
        
        Returns:
            PasswordValidationResult with validation details
        """
        feedback = []
        suggestions = []
        score = 0
        
        # Basic length check
        if len(password) < 8:
            feedback.append("Password must be at least 8 characters long")
            suggestions.append("Use at least 8 characters")
        elif len(password) >= 8:
            score += 1
        
        if len(password) >= 12:
            score += 1
        
        if len(password) >= 16:
            score += 1
        
        # Character variety checks
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in string.punctuation for c in password)
        
        char_types = sum([has_lower, has_upper, has_digit, has_special])
        
        if not has_lower:
            feedback.append("Add lowercase letters")
            suggestions.append("Include lowercase letters (a-z)")
        
        if not has_upper:
            feedback.append("Add uppercase letters")
            suggestions.append("Include uppercase letters (A-Z)")
        
        if not has_digit:
            feedback.append("Add numbers")
            suggestions.append("Include numbers (0-9)")
        
        if not has_special:
            feedback.append("Add special characters")
            suggestions.append("Include special characters (!@#$%^&*)")
        
        score += char_types
        
        # Pattern checks
        if self._has_repeated_chars(password):
            feedback.append("Avoid repeated characters")
            suggestions.append("Don't repeat the same character multiple times")
            score -= 1
        
        if self._has_sequential_chars(password):
            feedback.append("Avoid sequential characters")
            suggestions.append("Don't use sequential patterns like 'abc' or '123'")
            score -= 1
        
        if self._has_keyboard_patterns(password):
            feedback.append("Avoid keyboard patterns")
            suggestions.append("Don't use keyboard patterns like 'qwerty' or 'asdf'")
            score -= 2
        
        # Check against common passwords
        if self._is_common_password(password):
            feedback.append("This is a commonly used password")
            suggestions.append("Use a unique password that's not commonly used")
            score -= 3
        
        # Check against user information
        if user_info and self._contains_personal_info(password, user_info):
            feedback.append("Don't use personal information in passwords")
            suggestions.append("Avoid using your name, email, or other personal details")
            score -= 2
        
        # Dictionary word check
        if self._contains_dictionary_words(password):
            feedback.append("Avoid common dictionary words")
            suggestions.append("Use a combination of random words or create unique phrases")
            score -= 1
        
        # Calculate strength
        score = max(0, min(10, score))  # Clamp between 0-10
        
        if score <= 2:
            strength = PasswordStrength.VERY_WEAK
        elif score <= 4:
            strength = PasswordStrength.WEAK
        elif score <= 6:
            strength = PasswordStrength.FAIR
        elif score <= 8:
            strength = PasswordStrength.GOOD
        else:
            strength = PasswordStrength.STRONG
        
        is_valid = score >= 6 and len(password) >= 8
        
        if is_valid:
            feedback = ["Password meets security requirements"]
            suggestions = []
        
        return PasswordValidationResult(
            is_valid=is_valid,
            strength=strength,
            score=score,
            feedback=feedback,
            suggestions=suggestions
        )
    
    def generate_secure_password(self, length: int = 16, include_symbols: bool = True) -> str:
        """Generate a cryptographically secure password"""
        
        # Define character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        symbols = "!@#$%^&*()-_=+[]{}|;:,.<>?" if include_symbols else ""
        
        # Ensure at least one character from each set
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
        ]
        
        if include_symbols:
            password.append(secrets.choice(symbols))
        
        # Fill remaining length with random characters
        all_chars = lowercase + uppercase + digits + symbols
        for _ in range(length - len(password)):
            password.append(secrets.choice(all_chars))
        
        # Shuffle the password
        secrets.SystemRandom().shuffle(password)
        
        return ''.join(password)
    
    def _load_common_passwords(self) -> set:
        """Load common passwords list"""
        # Top 100 most common passwords
        common = {
            "password", "123456", "password123", "admin", "qwerty",
            "letmein", "welcome", "monkey", "1234567890", "123456789",
            "password1", "abc123", "Password", "password1!", "admin123",
            "root", "toor", "pass", "test", "guest", "info", "adm",
            "mysql", "qwerty123", "123qwe", "123abc", "qwe123",
            "1q2w3e4r", "1qaz2wsx", "qwertyuiop", "asdfghjkl",
            "zxcvbnm", "987654321", "1234567", "12345678", "12345",
            "1234", "123", "dragon", "pussy", "baseball", "football",
            "basketball", "superman", "michael", "jennifer", "joshua",
            "hunter", "fuckyou", "2000", "test123", "batman", "trustno1",
            "thomas", "robert", "access", "love", "buster", "1234567890",
            "soccer", "hockey", "killer", "george", "sexy", "andrew",
            "charlie", "superman", "asshole", "fuckyou", "dallas",
            "jessica", "panties", "pepper", "1111", "austin", "william",
            "daniel", "golfer", "summer", "heather", "hammer", "yankees",
            "joshua", "maggie", "biteme", "enter", "ashley", "thunder",
            "cowboy", "silver", "richard", "fucker", "orange", "merlin",
            "michelle", "corvette", "bigdog", "cheese", "matthew", "patrick",
            "martin", "freedom", "ginger", "blowjob", "nicole", "sparky",
            "yellow", "camaro", "secret", "dick", "falcon", "taylor",
            "111111", "131313", "123123", "bitch", "hello", "scooter",
            "please", "porsche", "guitar", "chelsea", "black", "diamond",
            "nascar", "jackson", "cameron", "654321", "computer", "amanda",
            "wizard", "xxxxxxxx", "money", "phoenix", "mickey", "bailey"
        }
        return common
    
    def _has_repeated_chars(self, password: str, threshold: int = 3) -> bool:
        """Check for repeated characters"""
        for i in range(len(password) - threshold + 1):
            if password[i:i+threshold] == password[i] * threshold:
                return True
        return False
    
    def _has_sequential_chars(self, password: str, threshold: int = 3) -> bool:
        """Check for sequential characters"""
        password_lower = password.lower()
        
        for i in range(len(password_lower) - threshold + 1):
            substring = password_lower[i:i+threshold]
            
            # Check ascending sequence
            if all(ord(substring[j+1]) == ord(substring[j]) + 1 for j in range(len(substring)-1)):
                return True
            
            # Check descending sequence
            if all(ord(substring[j+1]) == ord(substring[j]) - 1 for j in range(len(substring)-1)):
                return True
        
        return False
    
    def _has_keyboard_patterns(self, password: str) -> bool:
        """Check for keyboard patterns"""
        password_lower = password.lower()
        
        for pattern in self.keyboard_patterns:
            if pattern in password_lower or pattern[::-1] in password_lower:
                return True
        
        return False
    
    def _is_common_password(self, password: str) -> bool:
        """Check if password is in common passwords list"""
        return password.lower() in self.common_passwords
    
    def _contains_personal_info(self, password: str, user_info: Dict) -> bool:
        """Check if password contains personal information"""
        password_lower = password.lower()
        
        # Check email components
        if "email" in user_info:
            email_parts = user_info["email"].lower().split("@")[0].split(".")
            for part in email_parts:
                if len(part) > 2 and part in password_lower:
                    return True
        
        # Check name components
        if "name" in user_info:
            name_parts = user_info["name"].lower().split()
            for part in name_parts:
                if len(part) > 2 and part in password_lower:
                    return True
        
        # Check against personal patterns
        for pattern in self.personal_patterns:
            if re.search(pattern, password_lower):
                return True
        
        return False
    
    def _contains_dictionary_words(self, password: str) -> bool:
        """Check for common dictionary words (simplified)"""
        password_lower = password.lower()
        
        # Simple dictionary words check
        common_words = [
            "love", "hate", "good", "great", "best", "first", "last",
            "home", "work", "life", "time", "year", "day", "night",
            "black", "white", "red", "blue", "green", "yellow",
            "big", "small", "new", "old", "young", "high", "low"
        ]
        
        for word in common_words:
            if len(word) > 3 and word in password_lower:
                return True
        
        return False


# Global instance
password_validator = PasswordValidator()