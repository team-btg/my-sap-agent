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

@app.on_event("startup")
def startup():
    success = sap.login()
    if success:
        print("✅ SUCCESS: Backend logged into SAP Business One")
    else:
        print("❌ ERROR: Backend could not log into SAP. Check .env credentials.")

@app.get("/sap-status")
async def get_sap_status():
    # Attempt a lightweight call to check session
    is_connected = sap.login() # Or a lightweight GET like /b1s/v1/CompanyService_GetCompanyInfo
    if is_connected:
        return {"status": "Connected", "color": "green"}
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