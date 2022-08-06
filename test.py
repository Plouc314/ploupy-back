import os
import json
from dotenv import load_dotenv

load_dotenv()

r = os.environ["FIREBASE_CREDENTIALS"]
print(r[2300:2310])
print(json.loads(r))
