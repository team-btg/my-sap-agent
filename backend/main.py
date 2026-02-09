from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ai_agent import get_chat_response
from sap_service import sap

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, set this to your frontend URL
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    history: list = []

class LoginRequest(BaseModel):
    username: str
    password: str

@app.on_event("startup")
def startup():
    # Attempt login with ENV vars on startup
    sap.login()

@app.post("/login")
async def login(req: LoginRequest):
    success = sap.login(req.username, req.password)
    if success:
        return {"status": "success", "message": "Logged into SAP successfully"}
    else:
        return {"status": "error", "message": "Invalid SAP credentials"}

@app.get("/sap-status")
async def get_sap_status():
    # Do a lightweight query instead of re-authenticating
    try:
        result = sap.get_data("CompanyService_GetCompanyInfo")
        if "error" not in result:
            return {"status": "Connected", "color": "green"}
        else:
            return {"status": "Disconnected", "color": "red"}
    except Exception as e:
        return {"status": "Disconnected", "color": "red"}

@app.post("/chat") 
async def chat(req: ChatRequest):
    text, history, sap_json = get_chat_response(req.message, req.history)
    
    # Handle the unique "value" key in SAP responses
    cleaned_data = []
    if isinstance(sap_json, dict):
        cleaned_data = sap_json.get("value", [sap_json]) # Extract list or wrap single object
    elif isinstance(sap_json, list):
        cleaned_data = sap_json

    return {
        "reply": text, 
        "history": history, 
        "sap_json": cleaned_data
    }