from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import json
import os
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class POMScraperSelenium:
    def __init__(self):
        self.driver = None
        self.csrf_token = None
        self.is_ready = False
        self.link_1 = "https://pom.bpjsketenagakerjaan.go.id/pu/login?t=YTliOWM0OGNjMGExYWVlOTUyZGU2YTg5MjExNDk0YmFkYWZhOTQ0MzJkODZmZGUwYTY5OTNjMTUwMDI4MzIjMQ=="
        self.base_url = "https://pom.bpjsketenagakerjaan.go.id"
        
    def start_browser(self):
        """Start Chrome browser"""
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Untuk Termux, perlu mode headless
        chrome_options.add_argument("--headless")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        logger.info("Browser started")
        
    def full_login(self) -> dict:
        """Login otomatis menggunakan browser"""
        try:
            if not self.driver:
                self.start_browser()
            
            logger.info(f"Membuka: {self.link_1}")
            self.driver.get(self.link_1)
            time.sleep(3)
            
            logger.info(f"Current URL: {self.driver.current_url}")
            
            # Tunggu hingga halaman selesai load
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Extract CSRF token dari HTML
            html = self.driver.page_source
            csrf_pattern = r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']'
            match = re.search(csrf_pattern, html)
            
            if match:
                self.csrf_token = match.group(1)
                logger.info(f"CSRF Token: {self.csrf_token[:30]}...")
            
            # Akses step3
            logger.info("Mengakses step3...")
            self.driver.get(f'{self.base_url}/pu/step3')
            time.sleep(2)
            
            # Extract CSRF lagi jika perlu
            if not self.csrf_token:
                html2 = self.driver.page_source
                match2 = re.search(csrf_pattern, html2)
                if match2:
                    self.csrf_token = match2.group(1)
                    logger.info(f"CSRF Token from step3: {self.csrf_token[:30]}...")
            
            self.is_ready = True
            return {"status": "SUCCESS", "message": "Login berhasil!"}
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "ERROR", "message": str(e)}
    
    def check_kpj(self, kpj: str) -> dict:
        """Cek KPJ menggunakan browser"""
        if not self.is_ready:
            login = self.full_login()
            if login['status'] != 'SUCCESS':
                return login
        
        try:
            # Submit form
            url = f'{self.base_url}/pu/prosesHapusTkAll'
            
            # Buat payload
            payload = f'kpj={kpj}'
            if self.csrf_token:
                payload += f'&_csrf={self.csrf_token}'
            
            # Execute JavaScript untuk POST request
            js_code = f'''
            fetch("{url}", {{
                method: "POST",
                headers: {{
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Requested-With": "XMLHttpRequest"
                }},
                body: "{payload}"
            }})
            .then(response => response.json())
            .then(data => {{
                window.__result = data;
            }})
            .catch(error => {{
                window.__error = error.message;
            }});
            '''
            
            self.driver.execute_script(js_code)
            time.sleep(2)
            
            # Ambil hasil
            result = self.driver.execute_script("return window.__result;")
            error = self.driver.execute_script("return window.__error;")
            
            if error:
                return {"status": "ERROR", "message": error}
            
            if result:
                if result.get('ret') == '0':
                    return {"status": "SUCCESS", "data": result}
                else:
                    return {"status": "ERROR", "message": result.get('msg', 'KPJ tidak valid')}
            else:
                return {"status": "ERROR", "message": "Tidak ada response"}
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "ERROR", "message": str(e)}
    
    def close(self):
        if self.driver:
            self.driver.quit()


scraper = POMScraperSelenium()


# HTML
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
        h1 { text-align: center; color: #333; margin-bottom: 5px; }
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
        .success { background: #d4edda; color: #155724; padding: 10px; border-radius: 8px; }
        .error { background: #f8d7da; color: #721c24; padding: 10px; border-radius: 8px; }
        pre {
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 10px;
            border-radius: 8px;
            overflow-x: auto;
            font-size: 11px;
        }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        td { padding: 8px; border-bottom: 1px solid #ddd; }
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
            statusDiv.innerHTML = '⏳ Login... (buka browser)';
            statusDiv.className = 'status status-yellow';
            addLog('Mulai login...');
            
            try {
                const res = await fetch('/login', { method: 'POST' });
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
                    const fields = ['nik', 'nomorIdentitas', 'namaLengkap', 'nama', 'kpj', 'nomUpah', 'gaji'];
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


@app.route('/close', methods=['POST'])
def close():
    scraper.close()
    return jsonify({"status": "SUCCESS"})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("="*50)
    print("POM BPJS Scraper with Selenium")
    print(f"Buka: http://localhost:{port}")
    print("="*50)
    app.run(debug=False, host='0.0.0.0', port=port)
