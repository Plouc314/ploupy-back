from .config import *
from .exceptions import *
from .logger import LogConfig, logged
from .recorder import Recorder
from dotenv import load_dotenv

# importing env variables here has good chances of being
# soon enough...
if not FLAG_DEPLOY:
    load_dotenv()
