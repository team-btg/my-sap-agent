import requests
import os
import ssl
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
from dotenv import load_dotenv

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class LegacyAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs): 
        context = create_urllib3_context()
        
        context.set_ciphers('DEFAULT@SECLEVEL=0') 
         
        context.minimum_version = ssl.TLSVersion.TLSv1
        context.maximum_version = ssl.TLSVersion.TLSv1_3 

        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        kwargs['ssl_context'] = context
        return super(LegacyAdapter, self).init_poolmanager(*args, **kwargs)

class SAPServiceLayer:

    def post_data(self, resource, data):
        url = f"{self.base_url}/{resource}"
        try:
            response = self.session.post(url, json=data, timeout=15)
            # If 401, the auto-relogin logic we added earlier will handle it
            if response.status_code == 401:
                if self.login():
                    response = self.session.post(url, json=data, timeout=15)
            
            return response.json()
        except Exception as e:
            return {"error": str(e)}
        
    def post_query_service(self, path, option):
        url = f"{self.base_url}/QueryService_PostQuery"
        payload = {
            "QueryPath": path,
            "QueryOption": option
        }
        try:
            response = self.session.post(url, json=payload, timeout=20)
            if response.status_code == 401:
                if self.login():
                    response = self.session.post(url, json=payload, timeout=20)
            
            # The service returns a string-based JSON response that needs parsing
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def __init__(self):
        self.base_url = os.getenv("SAP_BASE_URL").rstrip('/')
        self.session = requests.Session()
        # verify=False here works with the context above
        self.session.verify = False 
        self.session.mount("https://", LegacyAdapter())

    def login(self):
        url = f"{self.base_url}/Login"
        payload = {
            "CompanyDB": os.getenv("SAP_DB"),
            "UserName": os.getenv("SAP_USER"),
            "Password": os.getenv("SAP_PASSWORD")
        }
        try:
            # Added a short timeout to prevent hanging
            response = self.session.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                return True
            else:
                print(f"SAP Login HTTP Error: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Critical Connection Error: {e}")
            return False

    def get_data(self, resource, params=None):
        url = f"{self.base_url}/{resource}"
        
        if params:
            # Reverting to standard query parameter style (?) but keeping %20 for spaces
            # SAP Service Layer often fails with + (plus) in query strings
            from urllib.parse import urlencode, quote
            query_string = urlencode(params, safe='$', quote_via=quote).replace("+", "%20")
            full_url = f"{url}?{query_string}"
            
            print(f"🚀 DEBUG: Final SAP URL: {full_url}")
            response = self.session.get(full_url)

            if response.status_code == 401:
                print("🔄 Session expired. Re-logging into SAP...")
                if self.login():
                    print("✅ Re-login successful. Retrying query.")
                    response = self.session.get(full_url)
                else:
                    return {"error": "Authentication failed even after retry."}
                        
        else:
            print(f"Fetching SAP Data from URL: {url}")
            response = self.session.get(url)
            
            if response.status_code == 401:
                print("🔄 Session expired. Re-logging into SAP...")
                if self.login():
                    print("✅ Re-login successful. Retrying query.")
                    response = self.session.get(full_url)
                else:
                    return {"error": "Authentication failed even after retry."}
                   
        return response.json()

sap = SAPServiceLayer()