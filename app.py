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
        
        self.base_url = "https://pom.bpjsketenagakerjaan.go.id"
        self.session = requests.Session()
        self.csrf_token = None
        self.is_ready = False
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
        }

    def full_login(self) -> dict:
        """ONE CLICK: Login + Akses step3 sekaligus"""
        logger.info("Memulai proses login otomatis...")
        
        try:
            # Step 1: Buka LINK_1 (login dengan token)
            logger.info("Step 1: Membuka LINK_1...")
            response = self.session.get(self.link_1, headers=self.headers, timeout=30, allow_redirects=True)
            
            if response.status_code != 200:
                return {"status": "ERROR", "message": f"Gagal buka LINK_1 (HTTP {response.status_code})"}
            
            logger.info(f"Redirect ke: {response.url}")
            
            # Step 2: Extract CSRF token dari response
            csrf_pattern = r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']'
            match = re.search(csrf_pattern, response.text)
            
            if match:
                self.csrf_token = match.group(1)
                self.headers['Cookie'] = f'_csrf={self.csrf_token}'
                logger.info(f"CSRF Token: {self.csrf_token[:30]}...")
            
            # Step 3: Akses step3 langsung
            logger.info("Step 2: Mengakses step3...")
            response2 = self.session.get(f'{self.base_url}/pu/step3', headers=self.headers, timeout=30)
            
            if response2.status_code == 200:
                # Extract CSRF lagi jika perlu
                if not self.csrf_token:
                    match2 = re.search(csrf_pattern, response2.text)
                    if match2:
                        self.csrf_token = match2.group(1)
                        self.headers['Cookie'] = f'_csrf={self.csrf_token}'
                
                self.is_ready = True
                return {"status": "SUCCESS", "message": "Login berhasil! Siap cek KPJ.", "csrf": self.csrf_token is not None}
            else:
                return {"status": "ERROR", "message": f"Gagal akses step3 (HTTP {response2.status_code})"}
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "ERROR", "message": str(e)}

    def check_kpj(self, kpj: str) -> dict:
        """Cek KPJ"""
        if not self.is_ready:
            # Auto login jika belum
            login_result = self.full_login()
            if login_result['status'] != 'SUCCESS':
                return {"status": "ERROR", "message": "Login gagal: " + login_result.get('message', '')}
        
        try:
            url = f'{self.base_url}/pu/prosesHapusTkAll'
            payload = {'kpj': kpj, '_csrf': self.csrf_token}
            headers = {**self.headers, 'X-Requested-With': 'XMLHttpRequest'}
            
            response = self.session.post(url, data=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                
                if 'application/json' in content_type:
                    try:
                        data = response.json()
                        if data.get('ret') == '0':
                            return {"status": "SUCCESS", "data": data}
                        else:
                            return {"status": "ERROR", "message": data.get('msg', 'KPJ tidak valid')}
                    except:
                        pass
                
                # Cek teks response
                if 'success' in response.text.lower() or 'berhasil' in response.text.lower():
                    return {"status": "SUCCESS", "data": response.text[:500]}
                
                return {"status": "ERROR", "message": "Response tidak dikenali"}
            else:
                return {"status": "ERROR", "message": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}


scraper = POMScraper()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['POST'])
def login():
    """Endpoint login sekali jalan"""
    result = scraper.full_login()
    return jsonify(result)


@app.route('/check', methods=['POST'])
def check_kpj():
    data = request.get_json()
    kpj = data.get('kpj', '').strip()
    
    if not kpj or len(kpj) != 11 or not kpj.isdigit():
        return jsonify({"status": "ERROR", "message": "KPJ harus 11 digit angka!"})
    
    result = scraper.check_kpj(kpj)
    return jsonify(result)


@app.route('/status')
def status():
    return jsonify({
        "is_ready": scraper.is_ready,
        "csrf_available": scraper.csrf_token is not None
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
