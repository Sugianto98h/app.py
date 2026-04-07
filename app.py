from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import re
import json
import os
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class POMScraper:
    def __init__(self):
        # TOKEN - TIDAK DIUBAH
        self.step4_token_url = "https://pine.email-view.com/ck1/2d6f.5380c38bfab80c4f/d90443d0-2cee-11f1-a839-525400cbcb5e/d19140869f7db161ebe006743ce23f8b4b5b7fb2/2?e=tGdHzLA2427rjrQ2UU6emUWS%2FgKC2z2XSHOblwKa%2Bp%2BCPcx8x7h7BnOqq7YgWTqrV57WXvtRjGLRsSWlP1%2F1XChzwE7VbnOfSXQNdnhAL0q3Qlhv8Gcz7EFZCyaZFRPnjAE%2Bd9XZTupbrMhpjRIpXl4PoNdI8Iqm%2F2kLWLh08gfy2VEkhJs2F2QfqB%2ByP%2BzX"
        
        self.base_url = "https://pom.bpjsketenagakerjaan.go.id"
        self.session = requests.Session()
        self.csrf_token = None
        self.step4_activated = False
        self.step3_accessible = False
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
            'Referer': self.base_url,
        }

    def activate_step4(self) -> dict:
        logger.info("Step 1: Membuka token untuk aktivasi step4...")
        
        try:
            response = self.session.get(
                self.step4_token_url, 
                headers=self.headers, 
                timeout=30,
                allow_redirects=True
            )
            
            logger.info(f"Token GET - Status: {response.status_code}")
            
            if response.status_code == 200:
                self.step4_activated = True
                
                if 'pom.bpjsketenagakerjaan.go.id' in response.url:
                    logger.info("Berhasil redirect ke POM step4!")
                    
                    csrf_pattern = r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']'
                    match = re.search(csrf_pattern, response.text)
                    if match:
                        self.csrf_token = match.group(1)
                        self.headers['Cookie'] = f'_csrf={self.csrf_token}'
                        logger.info(f"CSRF Token: {self.csrf_token[:30]}...")
                    
                    return {"status": "success", "message": "Step4 activated! Session siap.", "csrf": self.csrf_token is not None}
                else:
                    return {"status": "partial", "message": "Token terbuka, tapi tidak redirect ke POM", "final_url": response.url}
            else:
                return {"status": "error", "message": f"Token gagal dibuka (HTTP {response.status_code})"}
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "error", "message": str(e)}

    def access_step3(self) -> dict:
        logger.info("Step 2: Mengakses step3...")
        
        if not self.step4_activated:
            return {"status": "error", "message": "Step4 belum diaktifkan. Jalankan activate_step4() dulu."}
        
        try:
            response = self.session.get(
                f'{self.base_url}/pu/step3',
                headers=self.headers,
                timeout=30
            )
            
            logger.info(f"GET /pu/step3 - Status: {response.status_code}")
            
            if response.status_code == 200:
                self.step3_accessible = True
                
                if not self.csrf_token:
                    csrf_pattern = r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']'
                    match = re.search(csrf_pattern, response.text)
                    if match:
                        self.csrf_token = match.group(1)
                        self.headers['Cookie'] = f'_csrf={self.csrf_token}'
                        logger.info(f"CSRF Token: {self.csrf_token[:30]}...")
                
                return {"status": "success", "message": "Step3 accessible! Siap cek KPJ.", "csrf": self.csrf_token is not None}
            else:
                return {"status": "error", "message": f"Step3 tidak bisa diakses (HTTP {response.status_code})"}
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "error", "message": str(e)}

    def check_kpj(self, kpj: str) -> dict:
        logger.info(f"Step 3: Mengecek KPJ: {kpj}")
        
        if not self.step3_accessible:
            return {"status": "ERROR", "message": "Step3 belum bisa diakses. Jalankan aktivasi step4 dan step3 dulu."}
        
        if not self.csrf_token:
            return {"status": "ERROR", "message": "CSRF token tidak ditemukan. Coba refresh session."}
        
        try:
            url = f'{self.base_url}/pu/prosesHapusTkAll'
            payload = {'kpj': kpj, '_csrf': self.csrf_token}
            headers = {**self.headers, 'X-Requested-With': 'XMLHttpRequest'}
            
            response = self.session.post(url, data=payload, headers=headers, timeout=30)
            logger.info(f"POST /pu/prosesHapusTkAll - Status: {response.status_code}")
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                
                if 'application/json' in content_type:
                    try:
                        return {"status": "SUCCESS", "data": response.json()}
                    except:
                        pass
                
                if 'success' in response.text.lower() or 'berhasil' in response.text.lower():
                    return {"status": "SUCCESS", "data": response.text[:1000]}
                
                return {"status": "HTML_RESPONSE", "data": response.text[:1000]}
            else:
                return {"status": "ERROR", "message": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "ERROR", "message": str(e)}


scraper = POMScraper()


@app.route('/')
def index():
    return render_template('index.html', 
                         token_preview=scraper.step4_token_url[:80] + "...",
                         step4_activated=scraper.step4_activated,
                         step3_accessible=scraper.step3_accessible)


@app.route('/activate-step4', methods=['POST'])
def activate_step4():
    return jsonify(scraper.activate_step4())


@app.route('/access-step3', methods=['POST'])
def access_step3():
    return jsonify(scraper.access_step3())


@app.route('/check', methods=['POST'])
def check_kpj():
    data = request.get_json()
    kpj = data.get('kpj', '').strip()
    
    if not kpj or len(kpj) != 11 or not kpj.isdigit():
        return jsonify({"status": "ERROR", "message": "KPJ harus 11 digit angka!"})
    
    return jsonify(scraper.check_kpj(kpj))


@app.route('/status')
def status():
    return jsonify({
        "step4_activated": scraper.step4_activated,
        "step3_accessible": scraper.step3_accessible,
        "csrf_available": scraper.csrf_token is not None
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
