from flask import Flask, request, jsonify, render_template_string
import requests
import re
import json
import os
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class POMScraper:
    def __init__(self):
        # URL TOKEN - TIDAK DIUBAH
        self.token_url = "https://pom.bpjsketenagakerjaan.go.id/pu/login?t=YTliOWM0OGNjMGExYWVlOTUyZGU2YTg5MjExNDk0YmFkYWZhOTQ0MzJkODZmZGUwYTY5OTNjMTUwMDI4MzIjMQ=="
        self.base_url = "https://pom.bpjsketenagakerjaan.go.id"
        self.step3_url = f"{self.base_url}/pu/step3"
        self.check_url = f"{self.base_url}/pu/prosesHapusTkAll"
        
        self.session = requests.Session()
        self.csrf_token = None
        self.is_logged_in = False
        
        # Headers seperti browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

    def login(self) -> dict:
        """Step 1: Buka token URL untuk login"""
        logger.info("="*50)
        logger.info("STEP 1: Membuka token URL...")
        logger.info(f"URL: {self.token_url}")
        
        try:
            # Buka token URL
            response = self.session.get(self.token_url, headers=self.headers, timeout=30, allow_redirects=True)
            
            logger.info(f"Response Status: {response.status_code}")
            logger.info(f"Final URL setelah redirect: {response.url}")
            
            if response.status_code != 200:
                return {"status": "ERROR", "message": f"Token URL gagal dibuka (HTTP {response.status_code})"}
            
            # Extract CSRF token dari response
            csrf_pattern = r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']'
            match = re.search(csrf_pattern, response.text)
            
            if match:
                self.csrf_token = match.group(1)
                self.headers['Cookie'] = f'_csrf={self.csrf_token}'
                logger.info(f"✅ CSRF Token ditemukan: {self.csrf_token[:30]}...")
            else:
                logger.warning("⚠️ CSRF Token tidak ditemukan di response")
            
            self.is_logged_in = True
            return {"status": "SUCCESS", "message": "Token berhasil dibuka!", "csrf": self.csrf_token is not None}
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "ERROR", "message": str(e)}

    def access_step3(self) -> dict:
        """Step 2: Akses halaman step3 setelah login"""
        logger.info("="*50)
        logger.info("STEP 2: Mengakses halaman step3...")
        
        if not self.is_logged_in:
            return {"status": "ERROR", "message": "Belum login. Jalankan login() dulu."}
        
        try:
            response = self.session.get(self.step3_url, headers=self.headers, timeout=30)
            
            logger.info(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                # Cek apakah response JSON error atau HTML
                if response.text.startswith('{'):
                    try:
                        data = response.json()
                        if data.get('ret') == '-1':
                            return {"status": "ERROR", "message": f"Step3 tidak bisa diakses: {data.get('msg')}"}
                    except:
                        pass
                
                # Extract CSRF token jika belum ada
                if not self.csrf_token:
                    csrf_pattern = r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']'
                    match = re.search(csrf_pattern, response.text)
                    if match:
                        self.csrf_token = match.group(1)
                        self.headers['Cookie'] = f'_csrf={self.csrf_token}'
                        logger.info(f"✅ CSRF Token dari step3: {self.csrf_token[:30]}...")
                
                return {"status": "SUCCESS", "message": "Step3 berhasil diakses!", "html_length": len(response.text)}
            else:
                return {"status": "ERROR", "message": f"Gagal akses step3 (HTTP {response.status_code})"}
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "ERROR", "message": str(e)}

    def check_kpj(self, kpj: str) -> dict:
        """Step 3: Cek data KPJ"""
        logger.info("="*50)
        logger.info(f"STEP 3: Mengecek KPJ: {kpj}")
        
        if not self.is_logged_in:
            login_result = self.login()
            if login_result['status'] != 'SUCCESS':
                return login_result
        
        try:
            # Siapkan payload
            payload = {'kpj': kpj}
            if self.csrf_token:
                payload['_csrf'] = self.csrf_token
            
            # Headers untuk AJAX request
            headers = {
                **self.headers,
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': self.step3_url,
                'Origin': self.base_url,
            }
            
            logger.info(f"POST ke: {self.check_url}")
            logger.info(f"Payload: {payload}")
            
            response = self.session.post(self.check_url, data=payload, headers=headers, timeout=30)
            
            logger.info(f"Response Status: {response.status_code}")
            logger.info(f"Response Body: {response.text[:300]}")
            
            if response.status_code == 200:
                # Coba parse JSON
                try:
                    data = response.json()
                    if data.get('ret') == '0':
                        # Sukses
                        result = {
                            "status": "SUCCESS",
                            "message": "Data ditemukan!",
                            "data": data
                        }
                        # Extract personal data jika ada
                        if 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                            result['personal'] = data['data'][0]
                        return result
                    else:
                        return {"status": "ERROR", "message": data.get('msg', 'KPJ tidak valid')}
                except json.JSONDecodeError:
                    # Jika response HTML
                    if 'success' in response.text.lower() or 'berhasil' in response.text.lower():
                        return {"status": "SUCCESS", "message": "Berhasil!", "data": response.text[:500]}
                    return {"status": "ERROR", "message": f"Response: {response.text[:100]}"}
            else:
                return {"status": "ERROR", "message": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "ERROR", "message": str(e)}

    def get_full_process(self, kpj: str) -> dict:
        """Jalankan seluruh proses: Login -> Step3 -> Cek KPJ"""
        # Step 1: Login dengan token
        login_result = self.login()
        if login_result['status'] != 'SUCCESS':
            return login_result
        
        # Step 2: Akses step3
        step3_result = self.access_step3()
        if step3_result['status'] != 'SUCCESS':
            return step3_result
        
        # Step 3: Cek KPJ
        check_result = self.check_kpj(kpj)
        return check_result


# Inisialisasi scraper
scraper = POMScraper()


# HTML Template (Sederhana tapi lengkap)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>POM BPJS Scraper</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
        }
        .card {
            background: white;
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 5px;
            font-size: 24px;
        }
        .sub {
            text-align: center;
            color: #666;
            margin-bottom: 25px;
            font-size: 13px;
        }
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
        .success { background: #d4edda; color: #155724; padding: 10px; border-radius: 8px; }
        .error { background: #f8d7da; color: #721c24; padding: 10px; border-radius: 8px; }
        pre {
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 10px;
            border-radius: 8px;
            overflow-x: auto;
            font-size: 11px;
            white-space: pre-wrap;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        td {
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }
        td:first-child {
            font-weight: bold;
            width: 35%;
            background: #f0f0f0;
        }
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
        hr {
            margin: 20px 0;
            border: none;
            border-top: 1px solid #ddd;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>🏦 POM BPJS Scraper</h1>
            <div class="sub">Buka Token → Step3 → Cek KPJ</div>
            
            <div id="status" class="status status-red">❌ Belum Login</div>
            
            <button id="loginBtn" class="btn-login" onclick="doFullProcess()">🚀 PROSES FULL (Login → Step3 → Cek KPJ)</button>
            
            <hr>
            
            <h3 style="margin-bottom: 15px;">🔍 Atau Cek KPJ Manual</h3>
            <input type="text" id="kpj" maxlength="11" placeholder="Nomor KPJ (11 digit)" autocomplete="off" value="22119520694">
            <button id="checkBtn" class="btn-check" onclick="checkKPJ()" disabled>🔍 CEK KPJ</button>
            
            <div id="result" class="result">
                <h4>📊 Hasil</h4>
                <div id="resultContent"></div>
            </div>
            
            <div id="log" class="log">
                <p>📋 Log akan muncul di sini...</p>
            </div>
        </div>
    </div>

    <script>
        let isLoggedIn = false;
        
        function addLog(msg) {
            const logDiv = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            logDiv.innerHTML += `<p>[${time}] ${msg}</p>`;
            logDiv.scrollTop = logDiv.scrollHeight;
        }
        
        function updateStatus(message, isSuccess) {
            const statusDiv = document.getElementById('status');
            if (isSuccess) {
                statusDiv.innerHTML = '✅ ' + message;
                statusDiv.className = 'status status-green';
            } else {
                statusDiv.innerHTML = '❌ ' + message;
                statusDiv.className = 'status status-red';
            }
        }
        
        async function doFullProcess() {
            const btn = document.getElementById('loginBtn');
            const checkBtn = document.getElementById('checkBtn');
            const kpj = document.getElementById('kpj').value.trim();
            
            if (!kpj || !/^\\d{11}$/.test(kpj)) {
                alert('Masukkan KPJ 11 digit angka!');
                return;
            }
            
            btn.disabled = true;
            updateStatus('Memproses... (Login → Step3 → Cek KPJ)', false);
            addLog('🚀 Memulai proses full...');
            addLog(`KPJ: ${kpj}`);
            
            try {
                const res = await fetch('/full-process', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ kpj: kpj })
                });
                
                const data = await res.json();
                addLog(`Response: ${JSON.stringify(data)}`);
                
                if (data.status === 'SUCCESS') {
                    isLoggedIn = true;
                    updateStatus('Berhasil! Data ditemukan.', true);
                    checkBtn.disabled = false;
                    showResult(data);
                } else {
                    updateStatus('Gagal: ' + data.message, false);
                    showResult({ status: 'ERROR', message: data.message });
                }
            } catch (err) {
                addLog('❌ Error: ' + err.message);
                updateStatus('Error: ' + err.message, false);
                showResult({ status: 'ERROR', message: err.message });
            } finally {
                btn.disabled = false;
            }
        }
        
        async function checkKPJ() {
            if (!isLoggedIn) {
                alert('Proses full dulu! Klik tombol "PROSES FULL"');
                return;
            }
            
            const kpj = document.getElementById('kpj').value.trim();
            if (!kpj || !/^\\d{11}$/.test(kpj)) {
                alert('Masukkan KPJ 11 digit angka!');
                return;
            }
            
            const btn = document.getElementById('checkBtn');
            btn.disabled = true;
            addLog(`Cek KPJ: ${kpj}`);
            
            try {
                const res = await fetch('/check', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ kpj: kpj })
                });
                
                const data = await res.json();
                addLog(`Response: ${JSON.stringify(data)}`);
                showResult(data);
            } catch (err) {
                addLog('Error: ' + err.message);
                showResult({ status: 'ERROR', message: err.message });
            } finally {
                btn.disabled = false;
            }
        }
        
        function showResult(data) {
            const resultDiv = document.getElementById('result');
            const contentDiv = document.getElementById('resultContent');
            
            if (data.status === 'SUCCESS') {
                let html = '<div class="success">✅ Data Ditemukan!</div>';
                
                let personal = data.personal || data.data;
                
                if (personal && typeof personal === 'object') {
                    html += '<tr>';
                    const fieldMap = {
                        'nik': 'NIK',
                        'nomorIdentitas': 'NIK',
                        'namaLengkap': 'Nama Lengkap',
                        'nama': 'Nama',
                        'kpj': 'KPJ',
                        'nomUpah': 'Gaji',
                        'gaji': 'Gaji',
                        'tanggalLahir': 'Tanggal Lahir',
                        'jenisKelamin': 'Jenis Kelamin',
                        'statusKawin': 'Status Kawin',
                        'alamat': 'Alamat'
                    };
                    
                    for (const [key, value] of Object.entries(personal)) {
                        if (fieldMap[key] || key.toLowerCase().includes('nama') || key.toLowerCase().includes('nik') || key.toLowerCase().includes('kpj')) {
                            const label = fieldMap[key] || key;
                            html += `<tr><td style="font-weight: bold">${label}</td><td>${escapeHtml(String(value))}</td></tr>`;
                        }
                    }
                    html += '\\u003c/table>';
                } else {
                    html += `<pre>${escapeHtml(JSON.stringify(data.data, null, 2))}</pre>`;
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
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/login', methods=['POST'])
def login():
    """Endpoint untuk login dengan token"""
    result = scraper.login()
    return jsonify(result)


@app.route('/step3', methods=['POST'])
def step3():
    """Endpoint untuk akses step3"""
    result = scraper.access_step3()
    return jsonify(result)


@app.route('/check', methods=['POST'])
def check():
    """Endpoint untuk cek KPJ (harus sudah login)"""
    data = request.get_json()
    kpj = data.get('kpj', '').strip()
    
    if not kpj or len(kpj) != 11 or not kpj.isdigit():
        return jsonify({"status": "ERROR", "message": "KPJ harus 11 digit angka!"})
    
    result = scraper.check_kpj(kpj)
    return jsonify(result)


@app.route('/full-process', methods=['POST'])
def full_process():
    """Endpoint untuk menjalankan seluruh proses: Login -> Step3 -> Cek KPJ"""
    data = request.get_json()
    kpj = data.get('kpj', '').strip()
    
    if not kpj or len(kpj) != 11 or not kpj.isdigit():
        return jsonify({"status": "ERROR", "message": "KPJ harus 11 digit angka!"})
    
    result = scraper.get_full_process(kpj)
    return jsonify(result)


@app.route('/status')
def status():
    return jsonify({
        "is_logged_in": scraper.is_logged_in,
        "csrf_available": scraper.csrf_token is not None
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("="*60)
    print("🏦 POM BPJS Scraper - FULL VERSION")
    print("="*60)
    print(f"📱 Buka di browser: http://localhost:{port}")
    print("="*60)
    app.run(debug=False, host='0.0.0.0', port=port)
