from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import re
import json
import os
import logging
import time

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class POMScraper:
    def __init__(self):
        # Token untuk membuka step4
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
        """Step 1: Buka token untuk mengaktifkan step4"""
        logger.info("Step 1: Membuka token untuk aktivasi step4...")
        logger.info(f"Token URL: {self.step4_token_url[:100]}...")
        
        try:
            # Buka token URL (ini akan mengaktifkan session di POM)
            response = self.session.get(
                self.step4_token_url, 
                headers=self.headers, 
                timeout=30,
                allow_redirects=True
            )
            
            logger.info(f"Token GET - Status: {response.status_code}")
            logger.info(f"Final URL after redirects: {response.url}")
            
            if response.status_code == 200:
                self.step4_activated = True
                
                # Cek apakah redirect ke POM step4
                if 'pom.bpjsketenagakerjaan.go.id' in response.url:
                    logger.info("Berhasil redirect ke POM step4!")
                    
                    # Extract CSRF dari response
                    csrf_pattern = r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']'
                    match = re.search(csrf_pattern, response.text)
                    if match:
                        self.csrf_token = match.group(1)
                        self.headers['Cookie'] = f'_csrf={self.csrf_token}'
                    
                    return {"status": "success", "message": "Step4 activated! Session siap.", "csrf": self.csrf_token is not None}
                else:
                    return {"status": "partial", "message": "Token terbuka, tapi tidak redirect ke POM", "final_url": response.url}
            else:
                return {"status": "error", "message": f"Token gagal dibuka (HTTP {response.status_code})"}
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "error", "message": str(e)}

    def access_step3(self) -> dict:
        """Step 2: Akses step3 setelah step4 aktif"""
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
                
                # Extract CSRF token jika belum ada
                if not self.csrf_token:
                    csrf_pattern = r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']'
                    match = re.search(csrf_pattern, response.text)
                    if match:
                        self.csrf_token = match.group(1)
                        self.headers['Cookie'] = f'_csrf={self.csrf_token}'
                
                return {"status": "success", "message": "Step3 accessible! Siap cek KPJ.", "csrf": self.csrf_token is not None}
            else:
                return {"status": "error", "message": f"Step3 tidak bisa diakses (HTTP {response.status_code})"}
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "error", "message": str(e)}

    def check_kpj(self, kpj: str) -> dict:
        """Step 3: Cek KPJ setelah step3 bisa diakses"""
        logger.info(f"Step 3: Mengecek KPJ: {kpj}")
        
        if not self.step3_accessible:
            return {"status": "ERROR", "message": "Step3 belum bisa diakses. Jalankan aktivasi step4 dan step3 dulu."}
        
        if not self.csrf_token:
            return {"status": "ERROR", "message": "CSRF token tidak ditemukan. Coba refresh session."}
        
        try:
            # Coba endpoint yang benar
            url = f'{self.base_url}/pu/prosesHapusTkAll'
            payload = {
                'kpj': kpj,
                '_csrf': self.csrf_token
            }
            
            headers = {**self.headers, 'X-Requested-With': 'XMLHttpRequest'}
            
            response = self.session.post(
                url,
                data=payload,
                headers=headers,
                timeout=30
            )
            
            logger.info(f"POST /pu/prosesHapusTkAll - Status: {response.status_code}")
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                
                if 'application/json' in content_type:
                    try:
                        result = response.json()
                        return {"status": "SUCCESS", "data": result}
                    except:
                        pass
                
                # Cek apakah response mengandung data yang dicari
                if 'success' in response.text.lower() or 'berhasil' in response.text.lower():
                    return {"status": "SUCCESS", "data": response.text[:1000]}
                
                return {"status": "HTML_RESPONSE", "data": response.text[:1000]}
            else:
                return {"status": "ERROR", "message": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "ERROR", "message": str(e)}


# Inisialisasi
scraper = POMScraper()


@app.route('/')
def index():
    return render_template('index.html', 
                         token_preview=scraper.step4_token_url[:80] + "...",
                         step4_activated=scraper.step4_activated,
                         step3_accessible=scraper.step3_accessible)


@app.route('/activate-step4', methods=['POST'])
def activate_step4():
    result = scraper.activate_step4()
    return jsonify(result)


@app.route('/access-step3', methods=['POST'])
def access_step3():
    result = scraper.access_step3()
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
        "step4_activated": scraper.step4_activated,
        "step3_accessible": scraper.step3_accessible,
        "csrf_available": scraper.csrf_token is not None
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)    return render_template('index.html', 
                         token_preview=connector.token_url[:80] + "...",
                         connection_status=connector.connected,
                         full_token=connector.token_url)


@app.route('/connect', methods=['POST'])
def connect():
    """Endpoint untuk konek ke server"""
    result = connector.connect_to_server()
    return jsonify(result)


@app.route('/check', methods=['POST'])
def check_kpj():
    data = request.get_json()
    kpj = data.get('kpj', '').strip()
    
    if not kpj or len(kpj) != 11 or not kpj.isdigit():
        return jsonify({"status": "ERROR", "message": "KPJ harus 11 digit angka!"})
    
    result = connector.check_kpj(kpj)
    return jsonify(result)


@app.route('/status')
def status():
    return jsonify({
        "connected": connector.connected,
        "token_url": connector.token_url[:100] + "..."
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=5000)                
                logger.info(f"POST {endpoint} - Status: {response.status_code}")
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    
                    if 'application/json' in content_type:
                        try:
                            return {"status": "SUCCESS", "data": response.json()}
                        except:
                            pass
                    
                    if 'success' in response.text.lower() or 'berhasil' in response.text.lower():
                        return {"status": "SUCCESS", "data": response.text[:500]}
                    
                    if 'csrf' in response.text.lower() or 'token' in response.text.lower():
                        return {"status": "ERROR", "message": "CSRF token invalid. Coba refresh halaman."}
                    
                    return {"status": "HTML_RESPONSE", "data": response.text[:500]}
                
                elif response.status_code == 403:
                    return {"status": "ERROR", "message": "Akses ditolak. Token mungkin expired."}
                
                elif response.status_code == 404:
                    continue
            
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
                         token_preview=scraper.token[:80] + "...",
                         connection_status=scraper.connected,
                         full_token=scraper.token)


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
        "csrf_token": scraper.csrf_token is not None,
        "token_length": len(scraper.token)
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)                
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
