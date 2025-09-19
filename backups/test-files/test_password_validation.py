#!/usr/bin/env python3
"""Test password validation functionality"""

from infrastructure.security.password_validator import password_validator

def test_password_strength():
    """Test password strength validation"""
    
    test_cases = [
        ("123456", "Very weak - common password"),
        ("password", "Very weak - common password"),
        ("qwerty123", "Weak - keyboard pattern"),
        ("Test1234", "Fair - missing special chars"),
        ("Test@1234", "Good - has all requirements"),
        ("MyS3cur3P@ssw0rd!", "Strong - complex password"),
        ("aaaaaaa", "Very weak - repeated chars"),
        ("abcdefgh", "Weak - sequential chars"),
    ]
    
    print("🔍 Testing Password Strength Validation")
    print("=" * 60)
    
    for password, expected in test_cases:
        result = password_validator.validate_password(password)
        
        print(f"\nPassword: {password}")
        print(f"  Strength: {result.strength.name}")
        print(f"  Score: {result.score}/10")
        print(f"  Valid: {'✅' if result.is_valid else '❌'}")
        
        if result.feedback:
            print(f"  Feedback: {', '.join(result.feedback[:2])}")
        
        if result.suggestions:
            print(f"  Suggestion: {result.suggestions[0]}")
    
    # Test secure password generation
    print("\n" + "=" * 60)
    print("🔐 Generated Secure Passwords:")
    for i in range(3):
        secure_pwd = password_validator.generate_secure_password(16)
        print(f"  {i+1}. {secure_pwd}")
    
    print("\n✅ Password validation test complete")

if __name__ == "__main__":
    test_password_strength()