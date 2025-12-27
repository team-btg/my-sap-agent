from google import genai
from google.genai import types
from sap_service import sap
import os

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
 
def query_sap_resource(resource_name: str, query_params: dict = None):
    # Sanitize query_params: remove literal quotes from keys and values that Gemini sometimes adds
    if query_params:
        sanitized_params = {}
        for k, v in query_params.items():
            # Only strip if the entire string is wrapped in quotes
            new_k = k
            if isinstance(k, str):
                if (k.startswith('"') and k.endswith('"')) or (k.startswith("'") and k.endswith("'")):
                    new_k = k[1:-1]
            
            new_v = v
            if isinstance(v, str):
                if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                    new_v = v[1:-1]
            sanitized_params[new_k] = new_v
        query_params = sanitized_params

    print(f"🚀 SAP TOOL TRIGGERED: {resource_name}, {query_params}")
    data = sap.get_data(resource_name, params=query_params)
    return data 

def get_chat_response(message, history):
    # 1. Enhanced Tool Definition
    sap_tool = types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="query_sap_resource",
                description="Query SAP Business One Service Layer. Use for GET (fetching) and POST (creating).",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "resource_name": {
                            "type": "STRING", 
                            "description": "The SAP resource (e.g., Invoices, PurchaseInvoices, Items, Drafts)."
                        },
                        "query_params": {
                            "type": "OBJECT", 
                            "description": "OData query parameters. Example: {'$filter': \"DocNum eq 12345\", '$select': \"CardCode,DocTotal\", '$top': 10, '$orderby': \"DocDate desc\"}"
                        },
                        "method": {"type": "STRING", "enum": ["GET", "POST"], "description": "Default is GET. Use POST for creating Drafts."},
                        "body": {"type": "OBJECT", "description": "JSON payload for POST requests. For 'Drafts', MUST include 'DocObjectCode' (e.g., '22' for PO)."}
                    },
                    "required": ["resource_name"]
                }
            )
        ]
    )

    # 2. Reconstruct History with Data Context
    contents = []
    for turn in history:
        role = "user" if turn["role"] == "user" else "model"
        content_text = turn.get("content") or "..."
        
        # If there was SAP data in this turn, append a summary so the model 'remembers' IDs
        if turn.get("sapData"):
            data_summary = "\n[System Note: The previous response included SAP data. "
            if isinstance(turn["sapData"], list) and len(turn["sapData"]) > 0:
                # Just list the first few DocEntries/DocNums for context
                ids = [f"DocNum {d.get('DocNum')}(DocEntry {d.get('DocEntry')})" for d in turn["sapData"][:5] if d.get('DocNum')]
                data_summary += f"Found IDs: {', '.join(ids)}]"
            elif isinstance(turn["sapData"], dict):
                data_summary += f"Found ID: DocNum {turn['sapData'].get('DocNum')}(DocEntry {turn['sapData'].get('DocEntry')})]"
            content_text += data_summary

        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=content_text)]))
    
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message or "...")]))

    # 3. Call Gemini 3 with Cross-Join instructions
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction="""You are an expert SAP Business One consultant.

            CRITICAL: SEARCHING FOR A SPECIFIC RECORD
            - If the user asks about a specific document (e.g., 'What is in invoice 123?'), you MUST use '$filter'.
            - Example: query_sap_resource(resource_name='Invoices', query_params={'$filter': "DocNum eq 71015430"})
            - PREFER DocEntry if available in history: {'$filter': "DocEntry eq 30019"}.

            COMPLEX QUERIES & LINE-ITEM ANALYSIS:
            - For requests like 'Top Items', 'Most Purchased', or 'Find invoices with item X', use standard GET requests.
            - CRITICAL: The '$expand' parameter is NOT supported in this SAP version. NEVER use it.
            - To see line items for a specific document, you must query the resource directly (e.g., 'Invoices') and the lines will be included in the response by default in some SAP versions, or you may need to query the lines resource if the user asks for specific line details.
            - CROSS-JOIN: Use '$crossjoin(Resource1,Resource2)' as the resource_name if you need to filter headers by line properties.
            - Example for Item Search (No Expand):
              resource_name: "$crossjoin(Invoices,Invoices/DocumentLines)"
              query_params: {
                "$filter": "Invoices/DocEntry eq Invoices/DocumentLines/DocEntry and Invoices/DocumentLines/ItemCode eq 'ITEM_CODE'"
              }

            TRANSACTION RULES:
            - ALWAYS create documents as DRAFT using the 'Drafts' resource.
            - CRITICAL: When POSTing to 'Drafts', you MUST include the 'DocObjectCode' field in the root of the JSON body.
            - Purchase Order: DocObjectCode '22'.
            - Sales Invoice (A/R): DocObjectCode '13'.
            - Sales Order: DocObjectCode '17'.
            - Purchase Invoice (A/P): DocObjectCode '18'.
            - Example Draft Body: {"DocObjectCode": "22", "CardCode": "V1000", "DocumentLines": [{"ItemCode": "A001", "Quantity": 1}]}

            ODATA PRECISION:
            - NEVER use '$expand'. It is not supported.
            - RESOURCE PROPERTIES:
                - 'Items': Use 'PreferredVendor' (NOT 'CardCode') to find the vendor for an item.
                - 'Invoices'/'PurchaseInvoices': Use 'CardCode', 'CardName', 'DocTotal', 'DocDate'.
            - Strings MUST be in single quotes: CardCode eq 'V10000'.
            - Numbers MUST NOT have quotes: DocNum eq 12345.
            - Resource names are case-sensitive (e.g., 'Invoices', 'PurchaseInvoices').

            REPORTING RULES:
            - After calling a tool, ALWAYS explain the result to the user in a full sentence.
            - If you found a specific document, summarize its key details (Vendor, Date, Total, Items).
            - ALWAYS use Markdown tables for any tabular data or lists of records.
            """,
            tools=[sap_tool],
            thinking_config=types.ThinkingConfig(include_thoughts=True),
        )
    )

    final_sap_data = None
    
    # 4. Handle Tool Calls
    if response.candidates and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.function_call:
                fn = part.function_call
                try:
                    method = fn.args.get('method', 'GET')
                    
                    if method.upper() == "POST":
                        final_sap_data = sap.post_data(fn.args['resource_name'], fn.args.get('body'))
                    else:
                        # Standard GET (handles cross-joins via resource_name)
                        final_sap_data = query_sap_resource(fn.args['resource_name'], fn.args.get('query_params'))
                    
                    tool_output = {"result": final_sap_data}

                except Exception as e:
                    tool_output = f"Connection Error: {str(e)}"

                # Feed data back for final summary
                response = client.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents=contents + [
                        response.candidates[0].content,
                        types.Content(
                            role="user", 
                            parts=[types.Part.from_function_response(
                                name="query_sap_resource",
                                response=tool_output
                            )]
                        )
                    ]
                )
                break

    # 5. Robust Text Extraction (Thoughts excluded)
    if response.candidates and response.candidates[0].content.parts:
        text_parts = [p.text for p in response.candidates[0].content.parts if p.text and not p.thought]
        final_text = "\n".join(text_parts).strip()
        
        if not final_text or final_text == "Action completed successfully.":
            if final_sap_data:
                if isinstance(final_sap_data, dict) and "DocNum" in final_sap_data:
                    final_text = f"I have found the details for document {final_sap_data['DocNum']}. Please see the details below."
                else:
                    final_text = "I have retrieved the records from SAP based on your search criteria. Please see the details in the table."
    else:
        final_text = "No response received."
    
    # 6. Build History
    updated_history = list(history)
    updated_history.append({"role": "user", "content": message})
    updated_history.append({"role": "model", "content": final_text})

    return final_text, updated_history, final_sap_data