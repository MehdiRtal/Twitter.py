class TweetNotFound(Exception):
    def __init__(self):
        super().__init__("Tweet not found.")

class UserNotFound(Exception):
    def __init__(self):
        super().__init__("User not found.")

class InvalidCredentials(Exception):
    def __init__(self):
        super().__init__("Invalid credentials.")

class InvalidToken(Exception):
    def __init__(self):
        super().__init__("Invalid token.")

class InvalidOTP(Exception):
    def __init__(self):
        super().__init__("Invalid OTP.")

class InvalidEmail(Exception):
    def __init__(self):
        super().__init__("Invalid email.")

class CaptchaFailed(Exception):
    def __init__(self):
        super().__init__("Captcha failed.")
