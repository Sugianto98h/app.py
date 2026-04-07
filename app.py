from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import json
import os
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class TokenConnector:
    def __init__(self):
        # ============================================================
        # TOKEN PERSIS SEPERTI YANG DIBERIKAN - TIDAK DIUBAH
        # ============================================================
        self.token_url = "https://pine.email-view.com/ck1/2d6f.5380c38bfab80c4f/d90443d0-2cee-11f1-a839-525400cbcb5e/d19140869f7db161ebe006743ce23f8b4b5b7fb2/2?e=tGdHzLA2427rjrQ2UU6emUWS%2FgKC2z2XSHOblwKa%2Bp%2BCPcx8x7h7BnOqq7YgWTqrV57WXvtRjGLRsSWlP1%2F1XChzwE7VbnOfSXQNdnhAL0q3Qlhv8Gcz7EFZCyaZFRPnjAE%2Bd9XZTupbrMhpjRIpXl4PoNdI8Iqm%2F2kLWLh08gfy2VEkhJs2F2QfqB%2ByP%2BzX"
        
        self.session = requests.Session()
        self.connected = False
        self.response_data = None
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
        }

    def connect_to_server(self) -> dict:
        """Menghubungkan token ke server asalnya (pine.email-view.com)"""
        logger.info(f"Menghubungkan token ke: {self.token_url[:100]}...")
        
        try:
            # GET request ke token URL
            response = self.session.get(
                self.token_url, 
                headers=self.headers, 
                timeout=30,
                allow_redirects=True
            )
            
            logger.info(f"GET - Status: {response.status_code}")
            logger.info(f"Response Content-Type: {response.headers.get('Content-Type', 'unknown')}")
            
            if response.status_code == 200:
                self.connected = True
                
                # Cek apakah response JSON atau HTML
                content_type = response.headers.get('Content-Type', '')
                
                if 'application/json' in content_type:
                    try:
                        self.response_data = response.json()
                        return {"status": "success", "message": "Connected! Response is JSON", "data": self.response_data}
                    except:
                        pass
                
                # Jika HTML, coba extract info
                if 'text/html' in content_type:
                    # Extract title
                    title_match = re.search(r'<title>(.*?)</title>', response.text, re.IGNORECASE)
                    title = title_match.group(1) if title_match else "No title"
                    
                    return {
                        "status": "success", 
                        "message": f"Connected! Response is HTML - {title}", 
                        "html_preview": response.text[:500],
                        "full_response": response.text
                    }
                
                # Default: simpan text response
                self.response_data = response.text[:1000]
                return {"status": "success", "message": "Connected!", "data": self.response_data}
                
            elif response.status_code == 404:
                return {"status": "error", "message": "Token tidak ditemukan (404) - Mungkin sudah expired"}
            
            elif response.status_code == 403:
                return {"status": "error", "message": "Akses ditolak (403) - Token tidak valid"}
            
            else:
                return {"status": "error", "message": f"Gagal konek (HTTP {response.status_code})"}
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            return {"status": "error", "message": f"Tidak dapat terhubung ke server: {e}"}
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "error", "message": str(e)}

    def check_kpj(self, kpj: str) -> dict:
        """Cek KPJ - ini hanya simulasi karena token ini untuk email viewer"""
        if not self.connected:
            return {"status": "ERROR", "message": "Belum terhubung ke server. Klik 'Konek ke Server' dulu."}
        
        # Karena token ini dari pine.email-view.com (email tracker),
        # tidak ada fungsi cek KPJ. Ini hanya simulasi.
        return {
            "status": "INFO", 
            "message": "Token ini dari pine.email-view.com (email tracking), bukan dari POM BPJS. Tidak bisa cek KPJ.",
            "token_connected_to": self.token_url[:100],
            "server_response": self.response_data
        }


# Inisialisasi
connector = TokenConnector()


@app.route('/')
def index():
    return render_template('index.html', 
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
