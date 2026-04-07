from flask import Flask, request, jsonify, render_template_string
import requests
import json
import os
import logging
import time
import re
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
]

class POMScraper:
    def __init__(self):
        self.token_url = "https://pom.bpjsketenagakerjaan.go.id/pu/login?t=YTliOWM0OGNjMGExYWVlOTUyZGU2YTg5MjExNDk0YmFkYWZhOTQ0MzJkODZmZGUwYTY5OTNjMTUwMDI4MzIjMQ=="
        self.step3_url = "https://pom.bpjsketenagakerjaan.go.id/pu/step3"
        self.check_url = "https://pom.bpjsketenagakerjaan.go.id/pu/prosesPendaftaranTkKPJ"
        self.input_tk_step1_url = "https://pom.bpjsketenagakerjaan.go.id/pu/input-tk-nik-step1"
        
        self.session = requests.Session()
        self.csrf_token = None
        self.is_logged_in = False
        self.last_request_time = 0
        self.min_delay = 2

    def _get_headers(self, referer=None):
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
        }
        if referer:
            headers['Referer'] = referer
        return headers

    def _wait(self):
        current_time = time.time()
        if current_time - self.last_request_time < self.min_delay:
            time.sleep(self.min_delay)
        self.last_request_time = time.time()

    def _extract_csrf(self, html):
        patterns = [
            r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']',
            r'_csrf["\']?\s*:\s*["\']([^"\']+)["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)
        return None

    def _extract_form_data(self, html):
        """Extract data from form di halaman input-tk-nik-step1"""
        data = {}
        
        # Extract NIK
        nik_pattern = r'name=["\']nik["\'][^>]*value=["\']([^"\']+)["\']'
        nik_match = re.search(nik_pattern, html)
        if nik_match:
            data['nik'] = nik_match.group(1)
        
        # Extract Nama
        nama_pattern = r'name=["\']nama["\'][^>]*value=["\']([^"\']+)["\']'
        nama_match = re.search(nama_pattern, html)
        if nama_match:
            data['nama'] = nama_match.group(1)
        
        # Extract Tanggal Lahir
        tgl_pattern = r'name=["\']tanggal_lahir["\'][^>]*value=["\']([^"\']+)["\']'
        tgl_match = re.search(tgl_pattern, html)
        if tgl_match:
            data['tanggal_lahir'] = tgl_match.group(1)
        
        # Extract Jenis Kelamin (dari select)
        jk_pattern = r'name=["\']jenis_kelamin["\'][^>]*>.*?<option[^>]*selected[^>]*value=["\']([^"\']+)["\']'
        jk_match = re.search(jk_pattern, html, re.DOTALL)
        if jk_match:
            data['jenis_kelamin'] = jk_match.group(1)
        
        # Extract Alamat
        alamat_pattern = r'name=["\']alamat["\'][^>]*value=["\']([^"\']+)["\']'
        alamat_match = re.search(alamat_pattern, html)
        if alamat_match:
            data['alamat'] = alamat_match.group(1)
        
        return data

    def login(self) -> dict:
        """Login: Buka token URL -> Buka step3"""
        logger.info("Memulai login...")
        
        try:
            # Step 1: Buka token URL
            logger.info("Step 1: Membuka token URL...")
            self._wait()
            resp1 = self.session.get(self.token_url, headers=self._get_headers(), timeout=30, allow_redirects=True)
            logger.info(f"Token URL Status: {resp1.status_code}")
            
            # Step 2: Buka step3
            logger.info("Step 2: Membuka step3...")
            self._wait()
            resp2 = self.session.get(self.step3_url, headers=self._get_headers(self.step3_url), timeout=30)
            logger.info(f"Step3 Status: {resp2.status_code}")
            
            # Extract CSRF token
            self.csrf_token = self._extract_csrf(resp2.text)
            
            if self.csrf_token:
                self.is_logged_in = True
                return {"status": "SUCCESS", "message": "Login berhasil!", "csrf": self.csrf_token[:30] + "..."}
            else:
                return {"status": "ERROR", "message": "CSRF token tidak ditemukan"}
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return {"status": "ERROR", "message": str(e)}

    def cek_kpj(self, kpj: str) -> dict:
        """Cek KPJ dan ambil data dari input-tk-nik-step1"""
        if not self.is_logged_in:
            login_result = self.login()
            if login_result['status'] != 'SUCCESS':
                return login_result

        self._wait()

        try:
            headers = {
                **self._get_headers(self.step3_url),
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://pom.bpjsketenagakerjaan.go.id',
            }

            payload = {
                'kpj': kpj,
                '_csrf': self.csrf_token
            }

            # Step 1: Kirim KPJ
            logger.info(f"Mengirim KPJ: {kpj}")
            response = self.session.post(self.check_url, data=payload, headers=headers, timeout=60)

            if response.status_code == 429:
                time.sleep(10)
                return self.cek_kpj(kpj)

            if response.status_code == 200:
                try:
                    data = response.json()
                    msg = data.get('msg', '').lower()
                    
                    if 'brute' in msg:
                        time.sleep(10)
                        return {"status": "ERROR", "message": "Terlalu banyak request"}

                    if data.get('ret') == '0':
                        logger.info("KPJ valid, mengambil data dari input-tk-nik-step1...")
                        
                        # Step 2: Ambil data dari halaman input-tk-nik-step1
                        self._wait()
                        form_response = self.session.get(
                            self.input_tk_step1_url, 
                            headers=self._get_headers(self.step3_url), 
                            timeout=30
                        )
                        
                        logger.info(f"Input-tk-nik-step1 Status: {form_response.status_code}")
                        
                        if form_response.status_code == 200:
                            # Extract data dari form HTML
                            personal_data = self._extract_form_data(form_response.text)
                            personal_data['kpj'] = kpj
                            personal_data['status'] = 'VALID'
                            
                            logger.info(f"Data ditemukan: {json.dumps(personal_data, indent=2)}")
                            
                            return {
                                "status": "SUCCESS", 
                                "message": "Data ditemukan!",
                                "data": personal_data
                            }
                        else:
                            return {"status": "ERROR", "message": f"Gagal mengambil form data (HTTP {form_response.status_code})"}

                    if data.get('ret') == '-1':
                        self.is_logged_in = False
                        return self.login()

                    return {"status": "ERROR", "message": data.get('msg', 'KPJ tidak valid')}
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON Error: {e}")
                    return {"status": "ERROR", "message": f"Response error: {response.text[:100]}"}
                    
            return {"status": "ERROR", "message": f"HTTP {response.status_code}"}

        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "ERROR", "message": str(e)}


scraper = POMScraper()


# HTML Template (sama seperti sebelumnya)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>POM BPJS - Cek KPJ</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 600px; margin: 0 auto; }
        .card {
            background: white;
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1 { text-align: center; color: #333; margin-bottom: 5px; font-size: 24px; }
        .sub { text-align: center; color: #666; margin-bottom: 25px; font-size: 13px; }
        
        .status {
            text-align: center;
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-weight: bold;
        }
        .status-red { background: #f8d7da; color: #721c24; }
        .status-green { background: #d4edda; color: #155724; }
        .status-yellow { background: #fff3cd; color: #856404; }
        
        button {
            width: 100%;
            padding: 14px;
            font-size: 16px;
            font-weight: bold;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            margin-bottom: 15px;
        }
        .btn-login { background: #28a745; color: white; }
        .btn-check { background: #667eea; color: white; }
        button:disabled { opacity: 0.6; cursor: not-allowed; }
        
        input {
            width: 100%;
            padding: 12px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 10px;
            text-align: center;
            letter-spacing: 2px;
            margin-bottom: 15px;
            box-sizing: border-box;
        }
        
        .result {
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
            display: none;
        }
        .result.show { display: block; }
        .success { background: #d4edda; color: #155724; padding: 10px; border-radius: 8px; margin-bottom: 15px; }
        .error { background: #f8d7da; color: #721c24; padding: 10px; border-radius: 8px; margin-bottom: 15px; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        td { padding: 10px; border-bottom: 1px solid #ddd; }
        td:first-child { font-weight: bold; width: 35%; background: #f0f0f0; }
        
        .log {
            background: #1a1a2e;
            color: #0f0;
            padding: 10px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 10px;
            max-height: 200px;
            overflow-y: auto;
            margin-top: 15px;
        }
        .log p { margin: 3px 0; }
        hr { margin: 20px 0; border: none; border-top: 1px solid #ddd; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>🔍 POM BPJS - Cek KPJ</h1>
            <div class="sub">Buka Token → Step3 → Cek KPJ → Ambil Data</div>
            
            <div id="status" class="status status-yellow">⏳ Belum login</div>
            
            <button id="loginBtn" class="btn-login" onclick="doLogin()">🔑 BUKA TOKEN & STEP3</button>
            
            <hr>
            
            <input type="text" id="kpj" maxlength="11" placeholder="Masukkan KPJ (11 digit)" autocomplete="off">
            <button id="checkBtn" class="btn-check" onclick="doCheck()" disabled>🔍 CEK KPJ</button>
            
            <div id="result" class="result">
                <h4>📊 Hasil</h4>
                <div id="resultContent"></div>
            </div>
            
            <div id="log" class="log">
                <p>📋 Klik tombol untuk memulai...</p>
                <p>📌 Alur: Token URL → Step3 → Cek KPJ → Ambil data dari input-tk-nik-step1</p>
            </div>
        </div>
    </div>

    <script>
        let isLoggedIn = false;
        
        function addLog(msg, isError = false) {
            const logDiv = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            const color = isError ? '#ff6b6b' : '#0f0';
            logDiv.innerHTML += `<p style="color: ${color}">[${time}] ${msg}</p>`;
            logDiv.scrollTop = logDiv.scrollHeight;
        }
        
        function updateStatus(message, statusType) {
            const statusDiv = document.getElementById('status');
            statusDiv.innerHTML = message;
            if (statusType === 'success') {
                statusDiv.className = 'status status-green';
            } else if (statusType === 'loading') {
                statusDiv.className = 'status status-yellow';
            } else {
                statusDiv.className = 'status status-red';
            }
        }
        
        function showResult(data) {
            const resultDiv = document.getElementById('result');
            const contentDiv = document.getElementById('resultContent');
            
            if (data.status === 'SUCCESS') {
                let html = '<div class="success">✅ Data Ditemukan!</div>';
                if (data.data) {
                    html += '<table>';
                    for (const [key, val] of Object.entries(data.data)) {
                        if (val) {
                            let label = key;
                            if (key === 'nik') label = 'NIK';
                            if (key === 'nama') label = 'Nama';
                            if (key === 'kpj') label = 'KPJ';
                            if (key === 'tanggal_lahir') label = 'Tanggal Lahir';
                            if (key === 'jenis_kelamin') label = 'Jenis Kelamin';
                            if (key === 'alamat') label = 'Alamat';
                            html += `<td><td style="font-weight: bold">${label}</td><td>${escapeHtml(String(val))}</td></tr>`;
                        }
                    }
                    html += '\\u003c/table>';
                }
                contentDiv.innerHTML = html;
            } else {
                contentDiv.innerHTML = `<div class="error">❌ ${escapeHtml(data.message || 'Error')}</div>`;
            }
            resultDiv.classList.add('show');
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        async function doLogin() {
            const btn = document.getElementById('loginBtn');
            const checkBtn = document.getElementById('checkBtn');
            
            btn.disabled = true;
            updateStatus('Login... (Token → Step3)', 'loading');
            addLog('🚀 Membuka token URL...');
            
            try {
                const res = await fetch('/login', { method: 'POST' });
                const data = await res.json();
                addLog(`Response: ${JSON.stringify(data)}`);
                
                if (data.status === 'SUCCESS') {
                    isLoggedIn = true;
                    updateStatus('✅ Login berhasil!', 'success');
                    checkBtn.disabled = false;
                    addLog('✅ Login sukses!');
                } else {
                    updateStatus('❌ Login gagal', 'error');
                    addLog(`❌ Gagal: ${data.message}`, true);
                }
            } catch (err) {
                addLog(`❌ Error: ${err.message}`, true);
                updateStatus('Error: ' + err.message, 'error');
            } finally {
                btn.disabled = false;
            }
        }
        
        async function doCheck() {
            if (!isLoggedIn) {
                alert('Login dulu!');
                return;
            }
            
            const kpj = document.getElementById('kpj').value.trim();
            if (!kpj || !/^\\d{11}$/.test(kpj)) {
                alert('Masukkan KPJ 11 digit angka!');
                return;
            }
            
            const btn = document.getElementById('checkBtn');
            btn.disabled = true;
            btn.innerHTML = '⏳ MENCARI...';
            updateStatus('Mencari data...', 'loading');
            addLog(`🔍 Cek KPJ: ${kpj}`);
            
            try {
                const res = await fetch('/check', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ kpj: kpj })
                });
                const data = await res.json();
                addLog(`Response: ${JSON.stringify(data)}`);
                showResult(data);
                updateStatus(data.status === 'SUCCESS' ? '✅ Data ditemukan' : '❌ ' + data.message, data.status === 'SUCCESS' ? 'success' : 'error');
            } catch (err) {
                addLog(`❌ Error: ${err.message}`, true);
                showResult({ status: 'ERROR', message: err.message });
            } finally {
                btn.disabled = false;
                btn.innerHTML = '🔍 CEK KPJ';
            }
        }
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/login', methods=['POST'])
def login():
    result = scraper.login()
    return jsonify(result)


@app.route('/check', methods=['POST'])
def check():
    data = request.get_json()
    kpj = data.get('kpj', '').strip()
    
    if not kpj or len(kpj) != 11 or not kpj.isdigit():
        return jsonify({"status": "ERROR", "message": "KPJ harus 11 digit angka!"})
    
    result = scraper.cek_kpj(kpj)
    return jsonify(result)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("="*50)
    print("🔍 POM BPJS - Cek KPJ")
    print(f"📱 Buka: http://localhost:{port}")
    print("📌 Alur: Token URL → Step3 → Cek KPJ → Ambil data dari input-tk-nik-step1")
    print("="*50)
    app.run(debug=False, host='0.0.0.0', port=port)
