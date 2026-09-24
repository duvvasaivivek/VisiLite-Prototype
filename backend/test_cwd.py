import os
from app.core.config import settings
print("CWD:", os.getcwd())
print("Model:", settings.llm_model)
