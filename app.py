from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import re
import json
import os
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class POMScraperWithToken:
    def __init__(self):
        # TOKEN - TIDAK DIUBAH
        self.token = "2d6f.5380c38bfab80c4f/d90443d0-2cee-11f1-a839-525400cbcb5e/d19140869f7db161ebe006743ce23f8b4b5b7fb2/2?e=tGdHzLA2427rjrQ2UU6emUWS%2FgKC2z2XSHOblwKa%2Bp%2BCPcx8x7h7BnOqq7YgWTqrV57WXvtRjGLRsSWlP1%2F1XChzwE7VbnOfSXQNdnhAL0q3Qlhv8Gcz7EFZCyaZFRPnjAE%2Bd9XZTupbrMhpjRIpXl4PoNdI8Iqm%2F2kLWLh08gfy2VEkhJs2F2QfqB%2ByP%2BzX"
        
        self.base_url = "https://pom.bpjsketenagakerjaan.go.id"
        self.session = requests.Session()
        self.csrf_token = None
        self.connected = False
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
            'Referer': f'{self.base_url}/pu/step3',
            'X-Token': self.token,
            'Authorization': f'Bearer {self.token}',
            'Cookie': f'token={self.token}',
            'Token': self.token,
            'X-Requested-With': 'XMLHttpRequest'
        }

    def connect_to_pom(self) -> dict:
        """Menghubungkan token ke POM BPJS"""
        logger.info("Menghubungkan token ke POM BPJS...")
        
        try:
            # Step 1: GET halaman utama
            response = self.session.get(
                f'{self.base_url}/pu/step3', 
                headers=self.headers, 
                timeout=30
            )
            
            logger.info(f"GET /pu/step3 - Status: {response.status_code}")
            
            if response.status_code == 200:
                # Extract CSRF token
                csrf_patterns = [
                    r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']',
                    r'_csrf["\']?\s*:\s*["\']([^"\']+)["\']',
                    r'csrf_token["\']?\s*:\s*["\']([^"\']+)["\']'
                ]
                
                for pattern in csrf_patterns:
                    match = re.search(pattern, response.text)
                    if match:
                        self.csrf_token = match.group(1)
                        break
                
                if self.csrf_token:
                    self.headers['Cookie'] = f'_csrf={self.csrf_token}; token={self.token}'
                    self.connected = True
                    logger.info(f"CSRF Token ditemukan: {self.csrf_token[:30]}...")
                    return {"status": "success", "message": "Connected to POM"}
                else:
                    logger.warning("CSRF token tidak ditemukan di response")
                    # Coba tetap lanjut tanpa CSRF
                    self.connected = True
                    return {"status": "partial", "message": "Connected but no CSRF token"}
            
            elif response.status_code == 403 or response.status_code == 401:
                logger.error(f"Token ditolak oleh server: {response.status_code}")
                return {"status": "error", "message": f"Token invalid atau expired (HTTP {response.status_code})"}
            
            else:
                return {"status": "error", "message": f"Gagal konek ke POM (HTTP {response.status_code})"}
                
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return {"status": "error", "message": str(e)}

    def check_kpj(self, kpj: str) -> dict:
        """Cek KPJ"""
        logger.info(f"Mengecek KPJ: {kpj}")
        
        if not self.connected:
            # Coba connect ulang
            conn_result = self.connect_to_pom()
            if conn_result['status'] != 'success':
                return {"status": "ERROR", "message": f"Tidak terhubung ke POM: {conn_result.get('message')}"}
        
        try:
            # Coba dengan endpoint yang benar
            endpoints = [
                '/pu/prosesHapusTkAll',
                '/pu/cekkpj',
                '/pu/checkKpj',
                '/api/checkKpj'
            ]
            
            for endpoint in endpoints:
                url = f'{self.base_url}{endpoint}'
                logger.info(f"Mencoba endpoint: {url}")
                
                payload = {'kpj': kpj}
                if self.csrf_token:
                    payload['_csrf'] = self.csrf_token
                
                response = self.session.post(
                    url,
                    data=payload,
                    headers=self.headers,
                    timeout=30
                )
                
                logger.info(f"POST {endpoint} - Status: {response.status_code}")
                
                if response.status_code == 200:
                    # Cek apakah response JSON atau HTML
                    content_type = response.headers.get('Content-Type', '')
                    
                    if 'application/json' in content_type:
                        try:
                            return {"status": "SUCCESS", "data": response.json()}
                        except:
                            pass
                    
                    # Jika HTML tapi ada indikasi sukses
                    if 'success' in response.text.lower() or 'berhasil' in response.text.lower():
                        return {"status": "SUCCESS", "data": response.text[:500]}
                    
                    # Jika HTML error
                    if 'csrf' in response.text.lower() or 'token' in response.text.lower():
                        return {"status": "ERROR", "message": "CSRF token invalid. Coba refresh halaman."}
                    
                    return {"status": "HTML_RESPONSE", "data": response.text[:500]}
                
                elif response.status_code == 403:
                    return {"status": "ERROR", "message": "Akses ditolak. Token mungkin expired."}
                
                elif response.status_code == 404:
                    continue  # Coba endpoint berikutnya
            
            return {"status": "ERROR", "message": "Semua endpoint gagal. Server POM mungkin berubah."}
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "ERROR", "message": str(e)}


# Inisialisasi scraper
scraper = POMScraperWithToken()
connection_result = scraper.connect_to_pom()
logger.info(f"Connection result: {connection_result}")


@app.route('/')
def index():
    return render_template('index.html', 
                         token_preview=scraper.token[:50] + "...",
                         connection_status=scraper.connected)


@app.route('/check', methods=['POST'])
def check_kpj():
    data = request.get_json()
    kpj = data.get('kpj', '').strip()
    
    if not kpj or len(kpj) != 11 or not kpj.isdigit():
        return jsonify({"status": "ERROR", "message": "KPJ harus 11 digit angka!"})
    
    result = scraper.check_kpj(kpj)
    return jsonify(result)


@app.route('/reconnect')
def reconnect():
    result = scraper.connect_to_pom()
    return jsonify(result)


@app.route('/health')
def health():
    return jsonify({
        "status": "healthy", 
        "connected": scraper.connected,
        "csrf_token": scraper.csrf_token is not None
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
