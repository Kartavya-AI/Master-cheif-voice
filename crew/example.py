from typing import Union,List, Dict
import json
from mem0 import MemoryClient
import os
from dotenv import load_dotenv
from crewai.tools import tool
# Load environment variables
load_dotenv()
client = MemoryClient(api_key= os.getenv("MEMORY_API_KEY"))
# Retrieve the 10 most recent memories
results = client.get_all(
    user_id="sahu",
)

print(results)