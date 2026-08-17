from fastapi import Depends

# In the future, this will extract a user from a JWT token in the Authorization header.
# For development, we return a static mock user.
async def get_current_user() -> str:
    return "user-123"
