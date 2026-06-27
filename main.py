from urllib import request
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal
from schemas import UserCreate, UserLogin, UserResponse, DietaryRestrictionBase,UserServingSelection
from crud import create_user, get_user_by_email, verify_password, get_all_dietary_restrictions,save_user_serving
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import List  # ✅ add this line
from models import User, DietaryRestriction,Serving,UserServing
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from database import get_db
from sqlalchemy import text  # ✅ add this import at the top if missing
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
from fastapi.security import HTTPBearer
from fastapi import Security
from models import SavedRecipe
from schemas import SaveRecipeRequest
import json

security = HTTPBearer(auto_error=False)

import os
print("📁 Current working directory:", os.getcwd())
print("📂 Static folder absolute path:", os.path.abspath("static"))

Base.metadata.create_all(bind=engine)

SECRET_KEY = "mysecretkey"  # change to something secure
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/signup", response_model=UserResponse)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = get_user_by_email(db, user.email)
    print("PASSWORD:", user.password)
    print("PASSWORD LENGTH:", len(user.password))
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = create_user(db, user.full_name, user.email, user.password)
    return new_user

@app.post("/login")
def login(request: UserLogin, db: Session = Depends(get_db)):
    user = get_user_by_email(db, request.email)
    if not user or not verify_password(request.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token_data = {
        "sub": user.email,
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": access_token, "token_type": "bearer","onboarding_completed": user.onboarding_completed,"user_id": user.id,"onboarding_step": user.onboarding_step,  }

@app.put("/user/{user_id}/complete_onboarding")
def complete_onboarding(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.onboarding_completed = True
    user.onboarding_step = 5
    db.commit()
    db.refresh(user)
    return {"message": "Onboarding completed successfully"}


@app.get("/dietary_restrictions", response_model=List[DietaryRestrictionBase])
def get_dietary_restrictions(request: Request, db: Session = Depends(get_db)):
    restrictions = get_all_dietary_restrictions(db)
    base_url = str(request.base_url).rstrip('/')
    for r in restrictions:
        if r.logo_path:
            r.logo_path = f"{base_url}/static/logos/{r.logo_path}"
    return restrictions


from schemas import UserDietarySelection
from crud import save_user_dietary_restrictions
from jose import jwt, JWTError

# ✅ Helper function to extract user ID from token
def get_current_user_id(token: str = Depends(lambda: None), db: Session = Depends(get_db)):
    if token is None:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid user")
        return user.id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
        

from sqlalchemy import text

@app.post("/user/dietary_restrictions")
def set_user_dietary_restrictions(
    selection: UserDietarySelection,
    db: Session = Depends(get_db),
    credentials: dict = Security(security)
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        print(f"✅ User ID: {user.id}")
        print(f"✅ Dietary IDs: {selection.dietary_ids}")

        for dietary_id in selection.dietary_ids:
            db.execute(
                text("INSERT INTO user_dietary_restrictions (user_id, dietary_id) VALUES (:user_id, :dietary_id)"),
                {"user_id": user.id, "dietary_id": dietary_id},
            )
        user.onboarding_step = 2
        db.commit()
        print("✅ Commit successful.")
        return {"message": "Dietary restrictions saved successfully"}

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


from schemas import AllergyBase
from crud import get_all_allergies

@app.get("/allergies", response_model=List[AllergyBase])
def get_all_allergies_endpoint(request: Request, db: Session = Depends(get_db)):
    allergies = get_all_allergies(db)
    base_url = str(request.base_url).rstrip('/')
    for a in allergies:
        if a.logo_path:
            a.logo_path = f"{base_url}/static/logos/{a.logo_path}"
    return allergies

from schemas import UserAllergySelection
from crud import save_user_allergies

@app.post("/user/allergies")
def set_user_allergies(
    selection: UserAllergySelection,
    db: Session = Depends(get_db),
    credentials: dict = Security(security)
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        print(f"✅ User ID: {user.id}")
        print(f"✅ Allergies IDs: {selection.allergy_ids}")

        for allergy_id in selection.allergy_ids:
            db.execute(
                text("INSERT INTO user_allergies (user_id, allergy_id) VALUES (:user_id, :allergy_id)"),
                {"user_id": user.id, "allergy_id": allergy_id},
            )
        user.onboarding_step = 3
        db.commit()
        print("✅ Commit successful.")
        return {"message": "Allergies saved successfully"}

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from schemas import ServingBase
from crud import get_all_servings

@app.get("/servings", response_model=List[ServingBase])
def get_all_servings_endpoint(request: Request, db: Session = Depends(get_db)):
    servings = get_all_servings(db)
    base_url = str(request.base_url).rstrip('/')
    for s in servings:
        if s.logo_path:
            s.logo_path = f"{base_url}/static/logos/{s.logo_path}"
    return servings

@app.post("/user/servings")
def set_user_servings(
    selection: UserServingSelection,
    db: Session = Depends(get_db),
    credentials: dict = Security(security)
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")

    token = credentials.credentials
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    family_count = selection.family_count
    serving = db.query(Serving).filter(Serving.id == selection.serving_id).first()
    if not serving:
        raise HTTPException(status_code=404, detail="Invalid serving_id")

    if family_count is None:
        if "just" in serving.name.lower():
            family_count = 1
        elif "couple" in serving.name.lower():
            family_count = 2
        elif "family" in serving.name.lower():
            raise HTTPException(status_code=400, detail="Family count required")

    save_user_serving(db, user.id, selection.serving_id, family_count)
    user.onboarding_step = 4
    db.commit()
    return {"message": "Serving preference saved successfully"}


# ===============================================
# 🧬 LAB RESULTS UPLOAD ENDPOINT
# ===============================================
from fastapi import UploadFile, File
from models import LabResult
import os

UPLOAD_DIR = "uploaded_lab_results"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload_lab_result")
async def upload_lab_result(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    credentials: dict = Security(security)
):
    # ✅ Check token
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # ✅ Only allow PDF
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        # ✅ Save file locally
        save_path = os.path.join(UPLOAD_DIR, f"user_{user.id}_{file.filename}")
        with open(save_path, "wb") as buffer:
            buffer.write(await file.read())

        # ✅ Save record in DB
        lab = LabResult(user_id=user.id, filename=file.filename)
        db.add(lab)
        db.commit()
        db.refresh(lab)

        return {"message": "Lab result uploaded successfully", "filename": file.filename}

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error uploading file: {e}")

# ===============================================
# 🧠 USER FINAL INFO RETRIEVAL ENDPOINTS
# ===============================================
from models import DietaryRestriction, Allergy, Serving, LabResult
from sqlalchemy import text

# 🔹 1. Get user's dietary restriction(s)
@app.get("/user/dietary_restrictions")
def get_user_dietary_restrictions(db: Session = Depends(get_db), credentials: dict = Security(security), request: Request = None):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")

    token = credentials.credentials
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    base_url = str(request.base_url).rstrip('/')
    results = db.execute(text("""
        SELECT d.id, d.name, d.logo_path
        FROM user_dietary_restrictions udr
        JOIN dietary_restrictions d ON udr.dietary_id = d.id
        WHERE udr.user_id = :uid
    """), {"uid": user.id}).fetchall()

    return {
        "dietary_restrictions": [
            {
                "id": r[0],
                "name": r[1],
                "logo_path": f"{base_url}/static/logos/{r[2]}" if r[2] else None
            }
            for r in results
        ]
    }


# 🔹 2. Get user's allergy restriction(s)
@app.get("/user/allergies")
def get_user_allergies(
    db: Session = Depends(get_db),
    credentials: dict = Security(security),
    request: Request = None
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")
    token = credentials.credentials

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    base_url = str(request.base_url).rstrip('/')
    results = db.execute(text("""
        SELECT a.id, a.name, a.logo_path
        FROM user_allergies ua
        JOIN allergies a ON ua.allergy_id = a.id
        WHERE ua.user_id = :uid
    """), {"uid": user.id}).fetchall()

    return {
        "allergies": [
            {
                "id": r[0],
                "name": r[1],
                "logo_path": f"{base_url}/static/logos/{r[2]}" if r[2] else None
            }
            for r in results
        ]
    }



# 🔹 3. Get user's serving preference
@app.get("/user/servings")
def get_user_serving(
    db: Session = Depends(get_db),
    credentials: dict = Security(security),
    request: Request = None
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")
    token = credentials.credentials

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    base_url = str(request.base_url).rstrip('/')
    result = db.execute(text("""
        SELECT s.id, s.name, s.logo_path, us.family_count
        FROM user_servings us
        JOIN servings s ON us.serving_id = s.id
        WHERE us.user_id = :uid
    """), {"uid": user.id}).fetchone()

    if not result:
        return {"servings": []}

    sid, name, logo, family_count = result

    # 🧠 Label adjustment for family count
    if "family" in name.lower() and family_count:
        name = f"Family of {family_count}"

    return {
        "servings": [{
            "id": sid,
            "name": name,
            "logo_path": f"{base_url}/static/logos/{logo}" if logo else None
        }]
    }



# 🔹 4. Get user's latest uploaded lab result
@app.get("/user/lab_result")
def get_user_lab_result(db: Session = Depends(get_db), credentials: dict = Security(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")
    token = credentials.credentials

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = (
        db.query(LabResult)
        .filter(LabResult.user_id == user.id)
        .order_by(LabResult.uploaded_at.desc())
        .first()
    )

    if not result:
        return {"lab_result": None}

    return {"lab_result": result.filename}

from sqlalchemy import text

@app.get("/user_info/{user_id}")
def get_user_info(user_id: int, request: Request, db: Session = Depends(get_db)):
    from sqlalchemy import text

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    base_url = str(request.base_url).rstrip('/')

    # ✅ Fetch Dietary Restrictions (with ID)
    diet_query = text("""
        SELECT d.id, d.name, d.logo_path
        FROM user_dietary_restrictions udr
        JOIN dietary_restrictions d ON udr.dietary_id = d.id
        WHERE udr.user_id = :user_id
    """)
    diets = [
        {
            "id": row[0],
            "name": row[1],
            "logo": f"{base_url}/static/logos/{row[2]}" if row[2] else None
        }
        for row in db.execute(diet_query, {"user_id": user_id}).fetchall()
    ]

    # ✅ Fetch Allergies (with ID)
    allergy_query = text("""
        SELECT a.id, a.name, a.logo_path
        FROM user_allergies ua
        JOIN allergies a ON ua.allergy_id = a.id
        WHERE ua.user_id = :user_id
    """)
    allergies = [
        {
            "id": row[0],
            "name": row[1],
            "logo": f"{base_url}/static/logos/{row[2]}" if row[2] else None
        }
        for row in db.execute(allergy_query, {"user_id": user_id}).fetchall()
    ]

    # ✅ Fetch Serving Preference
    serving_query = text("""
        SELECT s.id, s.name, s.logo_path, us.family_count
        FROM user_servings us
        JOIN servings s ON us.serving_id = s.id
        WHERE us.user_id = :user_id
    """)

    serving_result = db.execute(serving_query, {"user_id": user_id}).fetchone()

    serving = None
    if serving_result:
        sid, name, logo, family_count = serving_result

        # Adjust label for family
        if "family" in name.lower() and family_count:
            name = f"Family of {family_count}"

        serving = {
            "id": sid,
            "name": name,
            "logo": f"{base_url}/static/logos/{logo}" if logo else None,
            "family_count": family_count
        }

    # # ✅ Fetch latest lab result (optional)
    # lab_result = db.execute(
    #     text("""
    #         SELECT filename
    #         FROM lab_results
    #         WHERE user_id = :user_id
    #         ORDER BY uploaded_at DESC
    #         LIMIT 1
    #     """),
    #     {"user_id": user_id},
    # ).fetchone()

    # lab_result_filename = lab_result[0] if lab_result else None

    lab_result = db.execute(
        text("""
            SELECT filename, glucose, ldl, hdl, triglycerides, creatinine
            FROM lab_results
            WHERE user_id = :user_id
            ORDER BY uploaded_at DESC
            LIMIT 1
        """),
        {"user_id": user_id},
    ).fetchone()

    lab_data = None
    lab_status = None
    if lab_result:

        lab_data = {
            "filename": lab_result[0],
            "glucose": lab_result[1],
            "ldl": lab_result[2],
            "hdl": lab_result[3],
            "triglycerides": lab_result[4],
            "creatinine": lab_result[5],
        }

        lab_status = classify_lab_results({
            "Glucose": lab_result[1],
            "LDL": lab_result[2],
            "HDL": lab_result[3],
            "Triglycerides": lab_result[4],
            "Creatinine": lab_result[5],
        })

    # ✅ Final response
    # return {
    #     "user_id": user_id,
    #     "dietary_restrictions": diets,
    #     "allergies": allergies,
    #     "serving_preference": serving,   # 👈 ADD THIS
    #     "lab_result_filename": lab_result_filename,
    #     "lab_data": lab_data
    # }
    return {
        "user_id": user_id,
        "dietary_restrictions": diets,
        "allergies": allergies,
        "serving_preference": serving,
        "lab_data": lab_data,
        "lab_status": lab_status
    }


from sqlalchemy import text

# ===============================================
# 🗑️ DELETE a specific dietary restriction for a user
# ===============================================
@app.delete("/user/dietary_restrictions/{dietary_id}")
def delete_user_dietary_restriction(
    dietary_id: int,
    db: Session = Depends(get_db),
    credentials: dict = Security(security)
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")

    token = credentials.credentials
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        result = db.execute(
            text("DELETE FROM user_dietary_restrictions WHERE user_id = :uid AND dietary_id = :did"),
            {"uid": user.id, "did": dietary_id}
        )
        db.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Dietary restriction not found for this user")

        return {"message": "Dietary restriction deleted successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting dietary restriction: {e}")


# ===============================================
# 🗑️ DELETE a specific allergy for a user
# ===============================================
@app.delete("/user/allergies/{allergy_id}")
def delete_user_allergy(
    allergy_id: int,
    db: Session = Depends(get_db),
    credentials: dict = Security(security)
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")

    token = credentials.credentials
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        result = db.execute(
            text("DELETE FROM user_allergies WHERE user_id = :uid AND allergy_id = :aid"),
            {"uid": user.id, "aid": allergy_id}
        )
        db.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Allergy not found for this user")

        return {"message": "Allergy deleted successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting allergy: {e}")



from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import re, io, os, tempfile


# 🧠 Utility function – Extract biomarkers
def extract_lab_values(file_path: str):
    text = ""

    # If PDF
    if file_path.lower().endswith(".pdf"):
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text("text") + "\n"

        # If scanned (no text) → OCR
        if len(text.strip()) < 50:
            print("🟡 Scanned PDF detected — using OCR...")
            images = convert_from_path(file_path)
            for img in images:
                text += pytesseract.image_to_string(img)
        else:
            print("🟢 Text-based PDF detected — no OCR needed.")

    # If image
    else:
        print("🟡 Image detected — using OCR...")
        img = Image.open(file_path)
        text = pytesseract.image_to_string(img)

    # Clean text
    text = re.sub(r"\s+", " ", text)

    print("\n================ EXTRACTED TEXT ================\n")
    print(text)
    print("\n===============================================\n")

    # Regex patterns
    patterns = {
        "LDL": r"LDL[−\-]?C\s*(?:calculé)?\s*([\d.]+)",
        "HDL": r"HDL[−\-]?C\s*([\d.]+)",
        "Triglycerides": r"Triglyc[ée]rides\s*([\d.]+)",
        "Glucose": r"(?:Glucose|Fasting Glucose)\s*([\d.]+)",
        "Creatinine": r"Cr[ée]atinine\s*([\d.]+)"
    }

    extracted = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1)
            if re.match(r"^\d+(\.\d+)?$", val):
                extracted[key] = float(val)
            else:
                extracted[key] = val.capitalize()
        else:
            extracted[key] = None

    return extracted

def classify_lab_results(data):

    result = {}

    # LDL
    ldl = data.get("LDL")
    if ldl is not None:
        if ldl < 100:
            result["LDL_status"] = "Healthy"
        else:
            result["LDL_status"] = "High"

    # HDL
    hdl = data.get("HDL")
    if hdl is not None:
        if hdl < 40:
            result["HDL_status"] = "Low"
        elif hdl < 60:
            result["HDL_status"] = "Healthy"
        else:
            result["HDL_status"] = "High"

    # Triglycerides
    trig = data.get("Triglycerides")
    if trig is not None:
        if trig < 150:
            result["Triglycerides_status"] = "Healthy"
        else:
            result["Triglycerides_status"] = "High"

    # Glucose
    glucose = data.get("Glucose")
    if glucose is not None:
        if glucose < 100:
            result["Glucose_status"] = "Healthy"
        else:
            result["Glucose_status"] = "High"

    # Creatinine
    creatinine = data.get("Creatinine")
    if creatinine is not None:
        if creatinine < 0.6:
            result["Creatinine_status"] = "Low"
        elif creatinine <= 1.3:
            result["Creatinine_status"] = "Healthy"
        else:
            result["Creatinine_status"] = "High"

    return result

# ============================================
# 📍 FastAPI Endpoint
# ============================================
# @app.post("/upload_lab_result_extract")
# async def upload_lab_result_extract(file: UploadFile = File(...)):
#     try:
#         # Save uploaded file temporarily
#         with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
#             tmp.write(await file.read())
#             tmp_path = tmp.name

#         # Extract biomarkers
#         extracted_data = extract_lab_values(tmp_path)
#         statuses = classify_lab_results(extracted_data)

#         # Delete temp file
#         os.remove(tmp_path)

#         return {
#         "message": "Lab result processed successfully",
#         "data": extracted_data,
#         "status": statuses
#         }

#     except Exception as e:
#         print("❌ Error:", e)
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/upload_lab_result_extract")
# async def upload_lab_result_extract(
#     file: UploadFile = File(...),
#     db: Session = Depends(get_db),
#     credentials: dict = Security(security)
# ):
#     try:
#         # ✅ Check token
#         if not credentials:
#             raise HTTPException(status_code=401, detail="Missing token")

#         token = credentials.credentials
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         email = payload.get("sub")

#         user = db.query(User).filter(User.email == email).first()
#         if not user:
#             raise HTTPException(status_code=404, detail="User not found")

#         # ✅ Save uploaded file temporarily
#         with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
#             tmp.write(await file.read())
#             tmp_path = tmp.name

#         # ✅ Extract biomarkers
#         extracted_data = extract_lab_values(tmp_path)

#         # ✅ Delete temp file
#         os.remove(tmp_path)

#         # ✅ SAVE ONLY ONCE 🔥
#         lab = LabResult(
#             user_id=user.id,
#             filename=file.filename,
#             glucose=extracted_data.get("Glucose"),
#             ldl=extracted_data.get("LDL"),
#             hdl=extracted_data.get("HDL"),
#             triglycerides=extracted_data.get("Triglycerides"),
#             creatinine=extracted_data.get("Creatinine")
#         )

#         db.add(lab)
#         db.commit()
#         db.refresh(lab)

#         return {
#             "message": "Lab result processed & saved successfully",
#             "data": extracted_data
#         }

#     except Exception as e:
#         db.rollback()
#         print("❌ Error:", e)
#         raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload_lab_result_extract")
async def upload_lab_result_extract(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    credentials: dict = Security(security)
):
    try:
        # ✅ Check token
        if not credentials:
            raise HTTPException(status_code=401, detail="Missing token")

        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")

        user = db.query(User).filter(User.email == email).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # ✅ Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=os.path.splitext(file.filename)[1]
        ) as tmp:

            tmp.write(await file.read())
            tmp_path = tmp.name

        # ✅ Extract biomarkers
        extracted_data = extract_lab_values(tmp_path)

        # ✅ Generate statuses
        statuses = classify_lab_results(extracted_data)

        print("EXTRACTED DATA:", extracted_data)
        print("STATUSES:", statuses)

        # ✅ Delete temp file
        os.remove(tmp_path)

        # ✅ Save to DB
        lab = LabResult(
            user_id=user.id,
            filename=file.filename,
            glucose=extracted_data.get("Glucose"),
            ldl=extracted_data.get("LDL"),
            hdl=extracted_data.get("HDL"),
            triglycerides=extracted_data.get("Triglycerides"),
            creatinine=extracted_data.get("Creatinine")
        )

        db.add(lab)
        db.commit()
        db.refresh(lab)

        return {
            "message": "Lab result processed successfully",
            "data": extracted_data,
            "status": statuses
        }

    except Exception as e:
        db.rollback()
        print("❌ Error:", e)
        raise HTTPException(status_code=500, detail=str(e))
    
@app.delete("/user/lab_result")
def delete_lab_result(
    db: Session = Depends(get_db),
    credentials: dict = Security(security)
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")

    token = credentials.credentials
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")

    user = db.query(User).filter(User.email == email).first()

    lab = db.query(LabResult)\
        .filter(LabResult.user_id == user.id)\
        .order_by(LabResult.uploaded_at.desc())\
        .first()

    if not lab:
        raise HTTPException(status_code=404, detail="No lab result found")

    db.delete(lab)
    db.commit()

    return {"message": "Lab result deleted"}

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

@app.post("/google-login")
def google_login(data: dict, db: Session = Depends(get_db)):

    email = data.get("email")

    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    user = db.query(User).filter(User.email == email).first()

    # 🔐 Create token function inline (same as login)
    def generate_token(user_email):
        token_data = {
            "sub": user_email,
            "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        }
        return jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    if not user:
        # 🔥 NEW USER
        user = User(
            email=email,
            onboarding_completed=False,
            onboarding_step=1
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        return {
            "access_token": generate_token(user.email),
            "onboarding_completed": False,
            "user_id": user.id,
            "onboarding_step": user.onboarding_step
        }

    # 🔥 EXISTING USER
    return {
        "access_token": generate_token(user.email),
        "onboarding_completed": user.onboarding_completed,
        "onboarding_step": user.onboarding_step,
        "user_id": user.id
    }



@app.put("/user/servings")
def update_user_servings(
    selection: UserServingSelection,
    db: Session = Depends(get_db),
    credentials: dict = Security(security)
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")

    token = credentials.credentials
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    family_count = selection.family_count

    serving = db.query(Serving).filter(Serving.id == selection.serving_id).first()
    if not serving:
        raise HTTPException(status_code=404, detail="Invalid serving_id")

    # 🔥 Handle default counts
    if family_count is None:
        if "just" in serving.name.lower():
            family_count = 1
        elif "couple" in serving.name.lower():
            family_count = 2
        elif "family" in serving.name.lower():
            raise HTTPException(status_code=400, detail="Family count required")

    # 🔥 UPDATE existing row
    existing = db.query(UserServing).filter(UserServing.user_id == user.id).first()

    if not existing:
        raise HTTPException(status_code=404, detail="No existing serving to update")

    existing.serving_id = selection.serving_id
    existing.family_count = family_count

    db.commit()
    db.refresh(existing)

    return {"message": "Serving updated successfully"}

@app.post("/api/recipes/save")
def save_recipe(
    recipe: SaveRecipeRequest,
    db: Session = Depends(get_db)
):

    saved = SavedRecipe(
        user_id=recipe.user_id,
        recipe_name=recipe.recipe_name,
        ingredients=json.dumps(recipe.ingredients),
        steps=json.dumps(recipe.steps),

        calories=recipe.calories,
        protein=recipe.protein,
        carbs=recipe.carbs,
        fat=recipe.fat,

        servings=recipe.servings
    )

    db.add(saved)
    db.commit()

    return {"message": "Recipe saved successfully"}

@app.get("/recipes/user/{user_id}")
def get_saved_recipes(
    user_id: int,
    db: Session = Depends(get_db)
):

    recipes = (
        db.query(SavedRecipe)
        .filter(SavedRecipe.user_id == user_id)
        .order_by(SavedRecipe.created_at.desc())
        .all()
    )

    return recipes


from dotenv import load_dotenv
import os

load_dotenv()

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "noreply.nutritrack@gmail.com"
SMTP_PASSWORD = "ycfs zrzr zpax mcdn"

from pydantic import BaseModel
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from crud import pwd_context
import random

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    new_password: str

class VerifyOtpRequest(BaseModel):
    email: str
    otp: str

def hash_password(password: str):
    return pwd_context.hash(password)

def send_reset_email(receiver_email: str, otp: str):

    msg = MIMEMultipart()

    msg["From"] = SMTP_EMAIL
    msg["To"] = receiver_email
    msg["Subject"] = "NutriTrack Password Reset OTP"

    body = f"""
Hello,

Your NutriTrack password reset code is:

{otp}

This code expires in 10 minutes.

If you did not request a password reset, ignore this email.

NutriTrack Team
"""

    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)

@app.post("/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.email == request.email
    ).first()

    if not user:
        return {"message": "If account exists, OTP sent"}

    otp = str(random.randint(100000, 999999))

    user.reset_otp = otp
    user.reset_otp_expiry = datetime.utcnow() + timedelta(minutes=10)

    db.commit()

    send_reset_email(user.email, otp)

    return {"message": "OTP sent successfully"}

@app.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.email == request.email
    ).first()

    if not user:
        raise HTTPException(404, "User not found")

    if user.reset_otp != request.otp:
        raise HTTPException(400, "Invalid OTP")

    if datetime.utcnow() > user.reset_otp_expiry:
        raise HTTPException(400, "OTP expired")

    user.password = hash_password(request.new_password)

    user.reset_otp = None
    user.reset_otp_expiry = None

    db.commit()

    return {
        "message": "Password updated successfully"
    }
@app.post("/verify-reset-otp")
def verify_reset_otp(
    request: VerifyOtpRequest,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.email == request.email
    ).first()

    if not user:
        raise HTTPException(400, "Invalid OTP")

    if user.reset_otp != request.otp:
        raise HTTPException(400, "Invalid OTP")

    if datetime.utcnow() > user.reset_otp_expiry:
        raise HTTPException(400, "OTP expired")

    return {"message": "OTP verified"}

