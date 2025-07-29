from typing import Union, List, Dict, Any
import json
from mem0 import MemoryClient
import os
from dotenv import load_dotenv
from crewai.tools import tool
import warnings
from pydantic import PydanticDeprecatedSince20

# Suppress Pydantic warnings
warnings.filterwarnings("ignore", category=PydanticDeprecatedSince20)

# Load environment variables
load_dotenv()
client = MemoryClient(api_key=os.getenv("MEMORY_API_KEY"))

def check_user_exists(user_id: str) -> dict:
    """
    Check if a user exists in memory by trying to retrieve their memories
    """
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=PydanticDeprecatedSince20)
            
            print(f"DEBUG: Checking if user '{user_id}' exists...")
            
            # Try to get memories for this user
            memories = client.get_all(user_id=user_id, limit=1)
            
            result = {
                "user_exists": len(memories) > 0,
                "memory_count": len(memories),
                "user_id": user_id,
                "memories": memories
            }
            
            print(f"DEBUG: User check result: {result}")
            return result
            
    except Exception as e:
        print(f"DEBUG: Error checking user: {str(e)}")
        return {
            "user_exists": False,
            "error": str(e),
            "user_id": user_id
        }

def create_new_user_with_memory(user_id: str, initial_message: str = None) -> str:
    """
    Create a new user by adding an initial memory for them
    In Mem0, users are created implicitly when you first add memory for them
    """
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=PydanticDeprecatedSince20)
            
            print(f"DEBUG: Attempting to create new user '{user_id}'...")
            
            # Check if user already exists
            user_check = check_user_exists(user_id)
            if user_check["user_exists"]:
                return f"User '{user_id}' already exists with {user_check['memory_count']} memories"
            
            # Create initial message if not provided
            if not initial_message:
                initial_message = f"New user {user_id} has been created in the system"
            
            # Add initial memory to create the user
            messages = [{"role": "user", "content": initial_message}]
            
            print(f"DEBUG: Adding initial memory for new user: {messages}")
            result = client.add(messages=messages, user_id=user_id)
            
            print(f"DEBUG: Add result: {result}")
            
            # Verify user was created
            verification = check_user_exists(user_id)
            
            if verification["user_exists"]:
                return f"SUCCESS: New user '{user_id}' created with initial memory. Result: {result}"
            else:
                return f"ERROR: User creation failed. Add result: {result}"
                
    except Exception as e:
        error_msg = f"ERROR: Failed to create user '{user_id}': {str(e)}"
        print(f"DEBUG: {error_msg}")
        return error_msg

def list_all_users(limit: int = 100) -> str:
    """
    Attempt to list all users by getting memories and extracting unique user_ids
    Note: Mem0 doesn't have a direct "list users" API, so we infer from memories
    """
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=PydanticDeprecatedSince20)
            
            print(f"DEBUG: Attempting to list users...")
            
            # Try different approaches to get user information
            users_found = set()
            
            # Method 1: Try to get memories without user_id (might not work)
            try:
                all_memories = client.get_all(limit=limit)
                print(f"DEBUG: Retrieved {len(all_memories)} total memories")
                
                # Extract user_ids from memories if they contain this info
                for memory in all_memories:
                    if isinstance(memory, dict) and 'user_id' in memory:
                        users_found.add(memory['user_id'])
                        
            except Exception as e:
                print(f"DEBUG: Method 1 failed: {str(e)}")
            
            # Method 2: Try common user_ids that might exist
            test_users = ["dishes", "user", "default", "admin", "test"]
            for test_user in test_users:
                try:
                    memories = client.get_all(user_id=test_user, limit=1)
                    if memories and len(memories) > 0:
                        users_found.add(test_user)
                        print(f"DEBUG: Found user '{test_user}' with {len(memories)} memories")
                except:
                    pass
            
            if users_found:
                return f"Found {len(users_found)} users: {list(users_found)}"
            else:
                return "No users found. Note: Mem0 doesn't have a direct user listing API."
                
    except Exception as e:
        return f"ERROR: Failed to list users: {str(e)}"

def add_to_history_with_user_creation(content: Union[str, list, dict], user_id: str = "dishes") -> str:
    """
    Enhanced version that ensures user exists before adding memory
    """
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=PydanticDeprecatedSince20)
            
            print(f"DEBUG: Adding memory for user '{user_id}'...")
            
            # Check if this is a new user
            user_check = check_user_exists(user_id)
            is_new_user = not user_check["user_exists"]
            
            if is_new_user:
                print(f"DEBUG: New user detected: {user_id}")
            else:
                print(f"DEBUG: Existing user with {user_check['memory_count']} memories")
            
            # Process content
            if isinstance(content, str):
                messages = [{"role": "user", "content": content}]
            elif isinstance(content, list):
                messages = content
            elif isinstance(content, dict):
                messages = [content]
            else:
                return f"ERROR: Invalid content type: {type(content)}"
            
            print(f"DEBUG: Adding {len(messages)} messages for user '{user_id}'")
            
            # Add to memory
            result = client.add(messages=messages, user_id=user_id)
            print(f"DEBUG: Add result: {result}")
            
            # Verify the addition
            final_check = check_user_exists(user_id)
            
            status = "NEW USER CREATED" if is_new_user else "EXISTING USER UPDATED"
            
            return f"SUCCESS ({status}): User '{user_id}' now has {final_check['memory_count']} memories. Latest result: {result}"
            
    except Exception as e:
        return f"ERROR: Failed to add memory for user '{user_id}': {str(e)}"

def debug_user_creation_issue():
    """
    Comprehensive debug function to identify user creation issues
    """
    print("=== MEM0 USER CREATION DEBUG ===\n")
    
    # Test 1: Check current setup
    print("1. Testing basic setup...")
    api_key = os.getenv("MEMORY_API_KEY")
    if api_key:
        print(f"✅ API key found (length: {len(api_key)})")
    else:
        print("❌ API key not found")
        return
    
    # Test 2: Check if any users exist
    print("\n2. Checking existing users...")
    users_result = list_all_users()
    print(users_result)
    
    # Test 3: Try creating a test user
    print("\n3. Creating test user...")
    test_user_id = "debug_test_user"
    creation_result = create_new_user_with_memory(test_user_id, "This is a test message for debugging")
    print(creation_result)
    
    # Test 4: Verify test user exists
    print("\n4. Verifying test user creation...")
    verification = check_user_exists(test_user_id)
    print(f"User exists: {verification['user_exists']}")
    print(f"Memory count: {verification['memory_count']}")
    
    # Test 5: Try the enhanced add function
    print("\n5. Testing enhanced add function...")
    enhanced_result = add_to_history_with_user_creation("Another test message", "another_test_user")
    print(enhanced_result)
    
    print("\n=== DEBUG COMPLETE ===")

# Test functions
def test_specific_user_creation(user_id: str):
    """Test creating a specific user"""
    print(f"Testing user creation for: {user_id}")
    
    # Check before
    before = check_user_exists(user_id)
    print(f"Before: {before}")
    
    # Create
    result = create_new_user_with_memory(user_id, f"Initial setup for user {user_id}")
    print(f"Creation result: {result}")
    
    # Check after
    after = check_user_exists(user_id)
    print(f"After: {after}")
    
    return result

if __name__ == "__main__":
    debug_user_creation_issue()


# test

def test_specific_user_creation(user_id: str):
    """Test creating a specific user"""
    print(f"Testing user creation for: {user_id}")
    
    # Check before
    before = check_user_exists(user_id)
    print(f"Before: {before}")
    
    # Create
    result = create_new_user_with_memory(user_id, f"Initial setup for user {user_id}")
    print(f"Creation result: {result}")
    
    # Check after
    after = check_user_exists(user_id)
    print(f"After: {after}")
    
    return result

if __name__ == "__main__":
    debug_user_creation_issue()
    test_specific_user_creation("test_user_123")
    test_specific_user_creation("another_test_user")
