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
        self.link_1 = "https://pom.bpjsketenagakerjaan.go.id/pu/login?t=YTliOWM0OGNjMGExYWVlOTUyZGU2YTg5MjExNDk0YmFkYWZhOTQ0MzJkODZmZGUwYTY5OTNjMTUwMDI4MzIjMQ=="
        self.base_url = "https://pom.bpjsketenagakerjaan.go.id"
        self.session = requests.Session()
        self.csrf_token = None
        self.is_ready = False
        
        # Headers seperti browser real
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36',
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

    def full_login(self) -> dict:
        """Login otomatis dan akses step3"""
        logger.info("Memulai proses login...")
        
        try:
            # Step 1: Buka LINK_1 (login dengan token)
            logger.info("Membuka LINK_1...")
            response = self.session.get(self.link_1, headers=self.headers, timeout=30, allow_redirects=True)
            
            logger.info(f"Status: {response.status_code}")
            logger.info(f"Final URL: {response.url}")
            
            if response.status_code != 200:
                return {"status": "ERROR", "message": f"Gagal buka LINK_1 (HTTP {response.status_code})"}
            
            # Extract CSRF token
            csrf_pattern = r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']'
            match = re.search(csrf_pattern, response.text)
            
            if match:
                self.csrf_token = match.group(1)
                self.headers['Cookie'] = f'_csrf={self.csrf_token}'
                logger.info(f"CSRF Token: {self.csrf_token[:30]}...")
            
            # Step 2: Akses step3 langsung
            logger.info("Mengakses step3...")
            time.sleep(2)
            response2 = self.session.get(f'{self.base_url}/pu/step3', headers=self.headers, timeout=30)
            
            logger.info(f"Step3 Status: {response2.status_code}")
            
            if response2.status_code == 200:
                # Extract CSRF lagi jika belum
                if not self.csrf_token:
                    match2 = re.search(csrf_pattern, response2.text)
                    if match2:
                        self.csrf_token = match2.group(1)
                        self.headers['Cookie'] = f'_csrf={self.csrf_token}'
                        logger.info(f"CSRF Token from step3: {self.csrf_token[:30]}...")
                
                self.is_ready = True
                return {"status": "SUCCESS", "message": "Login berhasil! Step3 siap diakses.", "csrf": self.csrf_token is not None}
            else:
                return {"status": "ERROR", "message": f"Gagal akses step3 (HTTP {response2.status_code})"}
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "ERROR", "message": str(e)}

    def check_kpj(self, kpj: str) -> dict:
        """Cek KPJ via endpoint prosesHapusTkAll"""
        if not self.is_ready:
            login = self.full_login()
            if login['status'] != 'SUCCESS':
                return login
        
        try:
            url = f'{self.base_url}/pu/prosesHapusTkAll'
            payload = {'kpj': kpj}
            if self.csrf_token:
                payload['_csrf'] = self.csrf_token
            
            headers = {
                **self.headers,
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': f'{self.base_url}/pu/step3',
                'Origin': self.base_url,
            }
            
            logger.info(f"POST ke: {url}")
            logger.info(f"Payload: {payload}")
            
            response = self.session.post(url, data=payload, headers=headers, timeout=30)
            
            logger.info(f"Response Status: {response.status_code}")
            logger.info(f"Response Body: {response.text[:300]}")
            
            if response.status_code == 200:
                # Coba parse JSON
                try:
                    data = response.json()
                    if data.get('ret') == '0':
                        # Sukses, extract data
                        result = {"status": "SUCCESS", "data": data}
                        # Jika ada data array, coba extract
                        if 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                            result['personal'] = data['data'][0]
                        return result
                    else:
                        return {"status": "ERROR", "message": data.get('msg', 'KPJ tidak valid')}
                except json.JSONDecodeError:
                    # Jika response HTML, cek apakah sukses
                    if 'success' in response.text.lower() or 'berhasil' in response.text.lower():
                        return {"status": "SUCCESS", "data": response.text[:500]}
                    return {"status": "ERROR", "message": f"Response bukan JSON: {response.text[:100]}"}
            else:
                return {"status": "ERROR", "message": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "ERROR", "message": str(e)}

    def get_step3_html(self) -> str:
        """Ambil HTML step3 untuk ditampilkan"""
        if not self.is_ready:
            self.full_login()
        
        try:
            response = self.session.get(f'{self.base_url}/pu/step3', headers=self.headers, timeout=30)
            if response.status_code == 200:
                return response.text
            return f"<h3>Error: HTTP {response.status_code}</h3>"
        except Exception as e:
            return f"<h3>Error: {e}</h3>"


scraper = POMScraper()


# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
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
            max-width: 700px;
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
        .btn-step3 { background: #17a2b8; color: white; }
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
            max-height: 150px;
            overflow-y: auto;
        }
        .log p { margin: 3px 0; }
        .step3-frame {
            width: 100%;
            border: none;
            border-radius: 10px;
            margin-top: 15px;
        }
        hr {
            margin: 20px 0;
            border: none;
            border-top: 1px solid #ddd;
        }
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 11px;
            margin-left: 8px;
        }
        .badge-csrf { background: #e7f3ff; color: #0066cc; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>🏦 POM BPJS Scraper</h1>
            <div class="sub">Cek Data Peserta BPJS Ketenagakerjaan</div>
            
            <div id="status" class="status status-red">❌ Belum Login</div>
            
            <button id="loginBtn" class="btn-login" onclick="doLogin()">🔑 LOGIN & AMBIL SESSION</button>
            <button id="step3Btn" class="btn-step3" onclick="openStep3()" disabled>🌐 BUKA STEP3 DI TAB BARU</button>
            
            <hr>
            
            <h3 style="margin-bottom: 15px;">🔍 Cek KPJ Langsung</h3>
            <input type="text" id="kpj" maxlength="11" placeholder="Nomor KPJ (11 digit)" autocomplete="off">
            <button id="checkBtn" class="btn-check" onclick="checkKPJ()" disabled>🔍 CEK KPJ</button>
            
            <div id="result" class="result">
                <h4>📊 Hasil Pengecekan</h4>
                <div id="resultContent"></div>
            </div>
            
            <div id="log" class="log">
                <p>📋 Log akan muncul di sini...</p>
            </div>
        </div>
    </div>

    <script>
        let isLoggedIn = false;
        let csrfToken = null;
        
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
        
        async function doLogin() {
            const loginBtn = document.getElementById('loginBtn');
            const step3Btn = document.getElementById('step3Btn');
            const checkBtn = document.getElementById('checkBtn');
            
            loginBtn.disabled = true;
            updateStatus('Login...', false);
            addLog('Mulai login...');
            
            try {
                const res = await fetch('/login', { method: 'POST' });
                const data = await res.json();
                addLog(`Response: ${JSON.stringify(data)}`);
                
                if (data.status === 'SUCCESS') {
                    isLoggedIn = true;
                    csrfToken = data.csrf;
                    updateStatus('Login Berhasil! Siap cek KPJ.', true);
                    step3Btn.disabled = false;
                    checkBtn.disabled = false;
                    addLog('✅ Login sukses!');
                    if (csrfToken) {
                        addLog(`CSRF Token: ${csrfToken.substring(0, 30)}...`);
                    }
                } else {
                    updateStatus('Login Gagal: ' + data.message, false);
                    addLog('❌ Login gagal: ' + data.message);
                }
            } catch (err) {
                addLog('❌ Error: ' + err.message);
                updateStatus('Error: ' + err.message, false);
            } finally {
                loginBtn.disabled = false;
            }
        }
        
        function openStep3() {
            if (!isLoggedIn) {
                alert('Login dulu!');
                return;
            }
            addLog('Membuka step3 di tab baru...');
            window.open('/step3', '_blank');
        }
        
        async function checkKPJ() {
            if (!isLoggedIn) {
                alert('Login dulu!');
                return;
            }
            
            const kpj = document.getElementById('kpj').value.trim();
            if (!kpj || !/^\\d{11}$/.test(kpj)) {
                alert('Masukkan KPJ 11 digit angka!');
                return;
            }
            
            const checkBtn = document.getElementById('checkBtn');
            checkBtn.disabled = true;
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
                checkBtn.disabled = false;
            }
        }
        
        function showResult(data) {
            const resultDiv = document.getElementById('result');
            const contentDiv = document.getElementById('resultContent');
            
            if (data.status === 'SUCCESS') {
                let html = '<div class="success">✅ Data Ditemukan!</div>';
                
                // Cek personal data
                let personal = data.personal || data.data;
                
                if (personal && typeof personal === 'object') {
                    html += '<table>';
                    const fieldMap = {
                        'nik': 'NIK',
                        'nomorIdentitas': 'NIK',
                        'namaLengkap': 'Nama Lengkap',
                        'nama': 'Nama',
                        'kpj': 'KPJ',
                        'nomUpah': 'Gaji',
                        'gaji': 'Gaji',
                        'tanggalLahir': 'Tanggal Lahir',
                        'tglLahir': 'Tanggal Lahir',
                        'jenisKelamin': 'Jenis Kelamin',
                        'statusKawin': 'Status Kawin',
                        'alamat': 'Alamat'
                    };
                    
                    let found = false;
                    for (const [key, value] of Object.entries(personal)) {
                        if (fieldMap[key] || key.toLowerCase().includes('nama') || key.toLowerCase().includes('nik') || key.toLowerCase().includes('kpj')) {
                            found = true;
                            const label = fieldMap[key] || key;
                            html += `<tr><td style="font-weight: bold">${label}</td><td>${escapeHtml(String(value))}</td></tr>`;
                        }
                    }
                    
                    if (!found) {
                        html += `<tr><td colspan="2">${escapeHtml(JSON.stringify(personal, null, 2))}</td></tr>`;
                    }
                    html += '</table>';
                } else if (data.data) {
                    html += `<pre>${escapeHtml(JSON.stringify(data.data, null, 2))}</pre>`;
                } else {
                    html += `<pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
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
        
        document.getElementById('kpj').addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && isLoggedIn) checkKPJ();
        });
        
        // Auto check status on load
        fetch('/status').then(res => res.json()).then(data => {
            if (data.is_ready) {
                isLoggedIn = true;
                updateStatus('Already logged in!', true);
                document.getElementById('step3Btn').disabled = false;
                document.getElementById('checkBtn').disabled = false;
                addLog('✅ Session masih aktif');
            }
        }).catch(() => {});
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/login', methods=['POST'])
def login():
    result = scraper.full_login()
    return jsonify(result)


@app.route('/check', methods=['POST'])
def check():
    data = request.get_json()
    kpj = data.get('kpj', '').strip()
    
    if not kpj or len(kpj) != 11 or not kpj.isdigit():
        return jsonify({"status": "ERROR", "message": "KPJ harus 11 digit angka!"})
    
    result = scraper.check_kpj(kpj)
    return jsonify(result)


@app.route('/step3')
def step3():
    """Tampilkan halaman step3 langsung dari POM"""
    html = scraper.get_step3_html()
    return html


@app.route('/status')
def status():
    return jsonify({
        "is_ready": scraper.is_ready,
        "csrf_available": scraper.csrf_token is not None
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("="*50)
    print("POM BPJS Scraper Started!")
    print(f"Buka: http://localhost:{port}")
    print("="*50)
    app.run(debug=False, host='0.0.0.0', port=port)
