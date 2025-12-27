# SAP Business One AI Agent

An intelligent AI assistant built with Gemini 3 Flash (Preview) to interact with SAP Business One via the Service Layer. This agent can query inventory, analyze sales/purchase documents, and create draft transactions using natural language.

## 🚀 Features

- **Natural Language Queries**: Ask about stock levels, top-selling items, or specific invoices.
- **SAP Service Layer Integration**: Direct OData integration with support for complex filters and cross-joins.
- **Draft Creation**: Automatically generate Purchase Order or Sales Order drafts.
- **Interactive UI**: React-based chat interface with Markdown support and a "Data Explorer" modal for large SAP datasets.
- **Real-time Status**: Live monitoring of the SAP Service Layer connection.

## 🛠️ Tech Stack

- **Frontend**: React, Vite, Tailwind CSS, Axios, Marked (Markdown), DOMPurify.
- **Backend**: FastAPI, Google GenAI SDK (Gemini 3 Flash), Requests.
- **AI Model**: Gemini 3 Flash (Preview).

## 📋 Prerequisites

- SAP Business One with Service Layer enabled.
- Google Gemini API Key.
- Python 3.9+ and Node.js 18+.

## ⚙️ Setup Instructions

### 1. Backend Setup
1. Navigate to the `backend` folder.
2. Create a `.env` file:
   ```env
   GEMINI_API_KEY=your_gemini_api_key
   SAP_BASE_URL=https://your-sap-server:50000/b1s/v1
   SAP_DB=your_company_db
   SAP_USER=your_username
   SAP_PASSWORD=your_password
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

### 2. Frontend Setup
1. Navigate to the `frontend` folder.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```

## 📖 Usage Examples

- "Show me the top 5 sales invoices by total amount."
- "What is the current stock for item JVLMAC00R4?"
- "Find the last purchase price for item X."
- "Create a purchase order draft for 10 units of item Y."

## ⚠️ Security Note
This project uses a custom `LegacyAdapter` to handle older SAP SSL configurations. Ensure your Service Layer is secured and use environment variables for all credentials.
