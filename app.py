from flask import Flask, request, jsonify
import requests
import re
import json
import os
import logging

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
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
        }

    def full_login(self) -> dict:
        logger.info("Memulai proses login...")
        
        try:
            # Buka LINK_1
            response = self.session.get(self.link_1, headers=self.headers, timeout=30, allow_redirects=True)
            logger.info(f"Status: {response.status_code}, URL: {response.url}")
            
            if response.status_code != 200:
                return {"status": "ERROR", "message": f"HTTP {response.status_code}"}
            
            # Extract CSRF
            csrf_pattern = r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']'
            match = re.search(csrf_pattern, response.text)
            
            if match:
                self.csrf_token = match.group(1)
                self.headers['Cookie'] = f'_csrf={self.csrf_token}'
                logger.info(f"CSRF: {self.csrf_token[:30]}...")
            
            # Akses step3
            response2 = self.session.get(f'{self.base_url}/pu/step3', headers=self.headers, timeout=30)
            logger.info(f"Step3 Status: {response2.status_code}")
            
            if response2.status_code == 200:
                if not self.csrf_token:
                    match2 = re.search(csrf_pattern, response2.text)
                    if match2:
                        self.csrf_token = match2.group(1)
                        self.headers['Cookie'] = f'_csrf={self.csrf_token}'
                
                self.is_ready = True
                return {"status": "SUCCESS", "message": "Login berhasil!"}
            else:
                return {"status": "ERROR", "message": f"Step3 HTTP {response2.status_code}"}
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "ERROR", "message": str(e)}

    def check_kpj(self, kpj: str) -> dict:
        if not self.is_ready:
            login = self.full_login()
            if login['status'] != 'SUCCESS':
                return login
        
        try:
            url = f'{self.base_url}/pu/prosesHapusTkAll'
            payload = {'kpj': kpj}
            if self.csrf_token:
                payload['_csrf'] = self.csrf_token
            
            headers = {**self.headers, 'X-Requested-With': 'XMLHttpRequest'}
            
            response = self.session.post(url, data=payload, headers=headers, timeout=30)
            logger.info(f"Check Status: {response.status_code}")
            
            if response.status_code == 200:
                # Coba parse JSON
                try:
                    data = response.json()
                    if data.get('ret') == '0':
                        return {"status": "SUCCESS", "data": data}
                    else:
                        return {"status": "ERROR", "message": data.get('msg', 'KPJ tidak valid')}
                except:
                    # Jika bukan JSON, cek teks
                    if 'success' in response.text.lower():
                        return {"status": "SUCCESS", "data": response.text[:500]}
                    return {"status": "ERROR", "message": "Response bukan JSON"}
            else:
                return {"status": "ERROR", "message": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}


scraper = POMScraper()


# HTML langsung di sini
HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>POM BPJS Scraper</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            margin: 0;
        }
        .container {
            max-width: 500px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 10px;
        }
        .sub {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
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
            margin: 10px 0 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        td {
            padding: 8px;
            border-bottom: 1px solid #ddd;
        }
        td:first-child { font-weight: bold; width: 35%; background: #f0f0f0; }
        .log {
            background: #1a1a2e;
            color: #0f0;
            padding: 10px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 10px;
            margin-top: 20px;
            max-height: 150px;
            overflow-y: auto;
        }
        .log p { margin: 3px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏦 POM BPJS Scraper</h1>
        <div class="sub">Cek Data Peserta BPJS Ketenagakerjaan</div>
        
        <div id="status" class="status status-red">❌ Belum Login</div>
        
        <button id="loginBtn" class="btn-login" onclick="doLogin()">🔑 LOGIN & AMBIL SESSION</button>
        
        <input type="text" id="kpj" maxlength="11" placeholder="Nomor KPJ (11 digit)" autocomplete="off">
        
        <button id="checkBtn" class="btn-check" onclick="checkKPJ()" disabled>🔍 CEK KPJ</button>
        
        <div id="result" class="result">
            <div id="resultContent"></div>
        </div>
        
        <div id="log" class="log">
            <p>📋 Log akan muncul di sini...</p>
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
        
        async function doLogin() {
            const btn = document.getElementById('loginBtn');
            const statusDiv = document.getElementById('status');
            
            btn.disabled = true;
            statusDiv.innerHTML = '⏳ Login...';
            statusDiv.className = 'status status-yellow';
            addLog('Mulai login...');
            
            try {
                addLog('Mengirim request POST ke /login');
                const res = await fetch('/login', { method: 'POST' });
                addLog(`Response status: ${res.status}`);
                
                const data = await res.json();
                addLog(`Response: ${JSON.stringify(data)}`);
                
                if (data.status === 'SUCCESS') {
                    isLoggedIn = true;
                    statusDiv.innerHTML = '✅ Login Berhasil!';
                    statusDiv.className = 'status status-green';
                    document.getElementById('checkBtn').disabled = false;
                    addLog('✅ Login sukses!');
                } else {
                    statusDiv.innerHTML = '❌ Login Gagal: ' + data.message;
                    statusDiv.className = 'status status-red';
                    addLog('❌ Login gagal: ' + data.message);
                }
            } catch (err) {
                addLog('❌ Error: ' + err.message);
                statusDiv.innerHTML = '❌ Error: ' + err.message;
                statusDiv.className = 'status status-red';
            } finally {
                btn.disabled = false;
            }
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
                
                if (data.data) {
                    let d = data.data;
                    if (d.data) d = d.data;
                    
                    html += '<table>';
                    const fields = ['nik', 'nomorIdentitas', 'namaLengkap', 'nama', 'kpj', 'nomUpah', 'gaji', 'tanggalLahir', 'jenisKelamin'];
                    for (const key of fields) {
                        if (d[key]) {
                            let label = key;
                            if (key === 'nomorIdentitas') label = 'NIK';
                            if (key === 'namaLengkap') label = 'Nama';
                            if (key === 'nomUpah') label = 'Gaji';
                            html += `<tr><td>${label}</td><td>${escapeHtml(String(d[key]))}</td></tr>`;
                        }
                    }
                    html += '</table>';
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
        
        document.getElementById('kpj').addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && isLoggedIn) checkKPJ();
        });
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return HTML


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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("="*50)
    print("POM BPJS Scraper Started!")
    print(f"Buka: http://localhost:{port}")
    print("="*50)
    app.run(debug=False, host='0.0.0.0', port=port) 
