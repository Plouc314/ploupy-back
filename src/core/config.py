'''
Contains global configurations flags
'''

FLAG_DEPLOY: bool = False
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
