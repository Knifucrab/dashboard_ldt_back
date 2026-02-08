from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    
class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: str | None
    avatar: str | None    
    
class LoginResponse(BaseModel):
    user: UserResponse
    token: str