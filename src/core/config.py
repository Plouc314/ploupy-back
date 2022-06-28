'''
Contains global configurations flags
'''

VERSION: str = "0.1.0"
'''
Backend version
'''

FLAG_DEPLOY: bool = True
'''
Flag that indicates whether the backend is deploy or dev mode
'''

ALLOWED_ORIGINS: list[str] = [
    "http://localhost:3000",
    "https://ploupy.plouc314.ch",
    "https://ploupy-front.vercel.app",
]
'''
All allowed domains (for CORS)
'''
