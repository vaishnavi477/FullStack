from fastapi import FastAPI, Form, Depends, HTTPException, Request, Path
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from dotenv import load_dotenv
from openai import OpenAI
import os
from db import get_db, SessionLocal, engine
from models import User, Itinerary
from typing import List
from pydantic import BaseModel, EmailStr

# Load environment variables
load_dotenv()

# OpenAI API Key
# client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

# FastAPI setup
app = FastAPI()

# Jinja2 template setup
templates = Jinja2Templates(directory="templates")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Ensure database tables are created
User.metadata.create_all(bind=engine)
Itinerary.metadata.create_all(bind=engine)

# Utility functions
def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Routes
@app.get("/Blueprint", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/register")
async def register_user(username: str = Form(...), password: str = Form(...), email: str = Form(...), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    hashed_password = get_password_hash(password)
    new_user = User(username=username, password=hashed_password, email=email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User registered successfully"}

@app.post("/login")
async def login_user(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == email).first()  # Change username to email
    if not db_user or not verify_password(password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {"message": "Login successful", "user_id": db_user.id}


# @app.post("/generate-itinerary")
# async def generate_itinerary(destination: str = Form(...), interests: str = Form(...), start_date: str = Form(...), end_date: str = Form(...), budget: float = Form(...), db: Session = Depends(get_db)):
#     prompt = f"""
#     Create a travel itinerary for {destination} from {start_date} to {end_date} based on these interests: {interests}.
#     The budget is {budget}. Suggest attractions, activities, and dining options for each day.
#     """
    
#     response = client.chat.completions.create(
#         model="gpt-4",
#         messages=[
#             {"role": "system", "content": "You are a helpful travel assistant."},
#             {"role": "user", "content": prompt}
#         ],
#         max_tokens=250,
#         temperature=0.5
#     )

#     generated_itinerary = response.choices[0].message.content

#     itinerary = Itinerary(destination=destination, interests=interests, start_date=start_date, end_date=end_date, budget=budget, generated_itinerary=generated_itinerary)
#     db.add(itinerary)
#     db.commit()
#     db.refresh(itinerary)
    
#     return {"itinerary": generated_itinerary}

@app.post("/logout")
async def logout_user(db: Session = Depends(get_db)):
    # If you are using cookies, you can delete the session or access_token cookie like this:
    response = RedirectResponse(url='/Blueprint')  # Redirect to the home page (login page)
    response.delete_cookie("access_token")  # Clear the access token or session cookie

    return JSONResponse(content={"message": "Logged out successfully"}, status_code=200)

# Pydantic models for request validation
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
 
class UserUpdate(BaseModel):
    username: str | None = None
    email: EmailStr | None = None
    password: str | None = None

# Routes

@app.get("/users", response_model=list[UserCreate])
async def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@app.get("/users/{user_id}", response_model=UserCreate)
async def get_user(user_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# @app.post("/users", response_model=UserCreate)
# async def create_user(user: UserCreate, db: Session = Depends(get_db)):
#     existing_user = db.query(User).filter(User.email == user.email).first()
#     if existing_user:
#         raise HTTPException(status_code=400, detail="Email already in use")

#     hashed_password = get_password_hash(user.password)
#     new_user = User(username=user.username, email=user.email, password=hashed_password)
    
#     db.add(new_user)
#     db.commit()
#     db.refresh(new_user)
    
#     return new_user

@app.put("/users/{user_id}")
async def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.username:
        db_user.username = user.username
    if user.email:
        db_user.email = user.email
    if user.password:
        db_user.password = get_password_hash(user.password)

    db.commit()
    db.refresh(db_user)
    
    return {"message": "User updated successfully", "user": db_user}

@app.patch("/users/{user_id}")
async def partial_update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.username is not None:
        db_user.username = user.username
    if user.email is not None:
        db_user.email = user.email
    if user.password is not None:
        db_user.password = get_password_hash(user.password)

    db.commit()
    db.refresh(db_user)
    
    return {"message": "User updated successfully", "user": db_user}

@app.delete("/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(db_user)
    db.commit()
    
    return {"message": "User deleted successfully"}
