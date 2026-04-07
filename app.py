from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import re
import json
import os
import logging
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class POMScraper:
    def __init__(self):
        # LINK_1 dari kode WebView - TIDAK DIUBAH
        self.link_1 = "https://pom.bpjsketenagakerjaan.go.id/pu/login?t=YTliOWM0OGNjMGExYWVlOTUyZGU2YTg5MjExNDk0YmFkYWZhOTQ0MzJkODZmZGUwYTY5OTNjMTUwMDI4MzIjMQ=="
        
        # STEP_2_DETECT - URL yang dideteksi setelah login
        self.step_2_detect = "https://pom.bpjsketenagakerjaan.go.id/pu/step4"
        
        # LINK_2 - URL final setelah redirect
        self.link_2 = "https://pom.bpjsketenagakerjaan.go.id/pu/step3"
        
        self.base_url = "https://pom.bpjsketenagakerjaan.go.id"
        self.session = requests.Session()
        self.csrf_token = None
        self.step1_completed = False
        self.step4_detected = False
        self.step3_accessible = False
        
        # Decode token untuk info
        self.decoded_token = self._decode_token()
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
        }
    
    def _decode_token(self):
        """Decode parameter t= dari LINK_1"""
        try:
            # Extract token dari URL
            match = re.search(r't=([^&]+)', self.link_1)
            if match:
                encoded = match.group(1)
                decoded = base64.b64decode(encoded).decode('utf-8')
                return decoded
        except:
            pass
        return "Unable to decode"

    def step1_load_login(self) -> dict:
        """Step 1: Buka LINK_1 (login page dengan token)"""
        logger.info("Step 1: Membuka LINK_1 (login page)...")
        logger.info(f"URL: {self.link_1}")
        
        try:
            response = self.session.get(
                self.link_1,
                headers=self.headers,
                timeout=30,
                allow_redirects=True
            )
            
            logger.info(f"GET - Status: {response.status_code}")
            logger.info(f"Final URL: {response.url}")
            
            if response.status_code == 200:
                self.step1_completed = True
                
                # Cek apakah redirect ke step4
                if self.step_2_detect in response.url:
                    self.step4_detected = True
                    logger.info("Step4 detected! Redirect berhasil.")
                    
                    # Extract CSRF
                    csrf_pattern = r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']'
                    match = re.search(csrf_pattern, response.text)
                    if match:
                        self.csrf_token = match.group(1)
                        self.headers['Cookie'] = f'_csrf={self.csrf_token}'
                    
                    return {"status": "success", "message": "Login berhasil, redirect ke step4", "csrf": self.csrf_token is not None}
                else:
                    return {"status": "partial", "message": f"Login OK, tapi tidak redirect ke step4. Current URL: {response.url}"}
            else:
                return {"status": "error", "message": f"Gagal buka LINK_1 (HTTP {response.status_code})"}
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "error", "message": str(e)}

    def step2_access_step4(self) -> dict:
        """Step 2: Akses step4 (detected URL)"""
        logger.info("Step 2: Mengakses step4...")
        
        if not self.step1_completed:
            return {"status": "error", "message": "Step 1 belum dijalankan."}
        
        try:
            response = self.session.get(
                self.step_2_detect,
                headers=self.headers,
                timeout=30,
                allow_redirects=True
            )
            
            logger.info(f"GET /pu/step4 - Status: {response.status_code}")
            
            if response.status_code == 200:
                self.step4_detected = True
                
                # Extract CSRF
                csrf_pattern = r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']'
                match = re.search(csrf_pattern, response.text)
                if match:
                    self.csrf_token = match.group(1)
                    self.headers['Cookie'] = f'_csrf={self.csrf_token}'
                
                return {"status": "success", "message": "Step4 berhasil diakses", "csrf": self.csrf_token is not None}
            else:
                return {"status": "error", "message": f"Gagal akses step4 (HTTP {response.status_code})"}
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "error", "message": str(e)}

    def step3_access_step3(self) -> dict:
        """Step 3: Akses step3 (LINK_2)"""
        logger.info("Step 3: Mengakses step3...")
        
        if not self.step4_detected:
            return {"status": "error", "message": "Step4 belum terdeteksi. Jalankan step2 dulu."}
        
        try:
            response = self.session.get(
                self.link_2,
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
                
                return {"status": "success", "message": "Step3 berhasil diakses! Siap cek KPJ.", "csrf": self.csrf_token is not None}
            else:
                return {"status": "error", "message": f"Gagal akses step3 (HTTP {response.status_code})"}
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "error", "message": str(e)}

    def check_kpj(self, kpj: str) -> dict:
        """Step 4: Cek KPJ"""
        logger.info(f"Step 4: Mengecek KPJ: {kpj}")
        
        if not self.step3_accessible:
            return {"status": "ERROR", "message": "Step3 belum bisa diakses. Selesaikan step 1-3 dulu."}
        
        if not self.csrf_token:
            return {"status": "ERROR", "message": "CSRF token tidak ditemukan."}
        
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
                         link_1_preview=scraper.link_1[:80] + "...",
                         decoded_token=scraper.decoded_token,
                         step1_completed=scraper.step1_completed,
                         step4_detected=scraper.step4_detected,
                         step3_accessible=scraper.step3_accessible)


@app.route('/step1', methods=['POST'])
def step1():
    return jsonify(scraper.step1_load_login())


@app.route('/step2', methods=['POST'])
def step2():
    return jsonify(scraper.step2_access_step4())


@app.route('/step3', methods=['POST'])
def step3():
    return jsonify(scraper.step3_access_step3())


@app.route('/check', methods=['POST'])
def check_kpj():
    data = request.get_json()
    kpj = data.get('kpj', '').strip()
    
    if not kpj or len(kpj) != 11 or not kpj.isdigit():
        return jsonify({"status": "ERROR", "message": "KPJ harus 11 digit angka!"})
    
    return jsonify(scraper.check_kpj(kpj))


@app.route('/reset', methods=['POST'])
def reset():
    """Reset session"""
    scraper.step1_completed = False
    scraper.step4_detected = False
    scraper.step3_accessible = False
    scraper.csrf_token = None
    scraper.session = requests.Session()
    return jsonify({"status": "success", "message": "Session reset"})


@app.route('/status')
def status():
    return jsonify({
        "step1_completed": scraper.step1_completed,
        "step4_detected": scraper.step4_detected,
        "step3_accessible": scraper.step3_accessible,
        "csrf_available": scraper.csrf_token is not None,
        "link_1": scraper.link_1,
        "decoded_token": scraper.decoded_token
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
