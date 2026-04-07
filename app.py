from flask import Flask, request, jsonify, render_template_string, session
import requests
import json
import os
import logging
import time
import re
import random
import secrets
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# ==================== KONFIGURASI ====================
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
]

# Storage untuk data peserta (simulasi database)
DATA_STORAGE = []
RETRY_COUNT = {}

# ==================== CLASS POM SCRAPER ====================
class POMScraper:
    def __init__(self):
        self.token_url = "https://pom.bpjsketenagakerjaan.go.id/pu/login?t=YTliOWM0OGNjMGExYWVlOTUyZGU2YTg5MjExNDk0YmFkYWZhOTQ0MzJkODZmZGUwYTY5OTNjMTUwMDI4MzIjMQ=="
        self.step3_url = "https://pom.bpjsketenagakerjaan.go.id/pu/step3"
        self.check_url = "https://pom.bpjsketenagakerjaan.go.id/pu/prosesPendaftaranTkKPJ"
        
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

    def login(self) -> dict:
        """Full login flow: Token URL -> Step3 -> Step4 -> Step3"""
        logger.info("Memulai login flow...")
        
        try:
            # Step 1: Token URL
            self._wait()
            resp1 = self.session.get(self.token_url, headers=self._get_headers(), timeout=30, allow_redirects=True)
            logger.info(f"Token URL: {resp1.status_code}")
            
            # Step 2: Step3
            self._wait()
            resp2 = self.session.get(self.step3_url, headers=self._get_headers(self.step3_url), timeout=30)
            logger.info(f"Step3: {resp2.status_code}")
            
            # Step 3: Step4
            self._wait()
            resp3 = self.session.get(self.step4_url, headers=self._get_headers(self.step3_url), timeout=30)
            logger.info(f"Step4: {resp3.status_code}")
            
            # Step 4: Step3 lagi untuk CSRF
            self._wait()
            resp4 = self.session.get(self.step3_url, headers=self._get_headers(self.step3_url), timeout=30)
            logger.info(f"Step3 final: {resp4.status_code}")
            
            self.csrf_token = self._extract_csrf(resp4.text)
            
            if self.csrf_token:
                self.is_logged_in = True
                return {"status": "SUCCESS", "message": "Login berhasil!", "csrf": self.csrf_token[:30] + "..."}
            return {"status": "ERROR", "message": "CSRF token tidak ditemukan"}
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    def check_kpj(self, kpj: str) -> dict:
        """Cek KPJ"""
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
            
            payload = f'kpj={kpj}'
            if self.csrf_token:
                payload += f'&_csrf={self.csrf_token}'
            
            response = self.session.post(self.check_url, data=payload, headers=headers, timeout=60)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('ret') == '0':
                        result_data = data.get('data', [])
                        if result_data and len(result_data) > 0:
                            return {"status": "SUCCESS", "data": result_data[0]}
                    return {"status": "ERROR", "message": data.get('msg', 'KPJ tidak valid')}
                except:
                    return {"status": "ERROR", "message": "Response error"}
            return {"status": "ERROR", "message": f"HTTP {response.status_code}"}
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

# ==================== CLASS OSS SCRAPER ====================
class OSSScraper:
    def __init__(self):
        self.oss_url = "https://www.bpjsketenagakerjaan.go.id/oss?token=ZW1haWw9a29wdHRpd2FoeXVzYXRyaWEyMkBnbWFpbC5jb20mbmliPTE2MDkyMjAyMjA4MDk="
        self.session = requests.Session()

    def check_kpj(self, kpj: str) -> dict:
        """Cek KPJ via OSS"""
        logger.info(f"Mengecek KPJ via OSS: {kpj}")
        
        try:
            # Simulasi - implementasi sesuai kebutuhan
            return {"status": "INFO", "message": "Fitur OSS dalam pengembangan"}
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

# ==================== STORAGE FUNCTIONS ====================
def save_data(data: dict):
    """Simpan data peserta"""
    global DATA_STORAGE
    
    # Cek apakah sudah ada
    existing = None
    for i, item in enumerate(DATA_STORAGE):
        if item.get('kpj') == data.get('kpj'):
            existing = i
            break
    
    data['timestamp'] = datetime.now().isoformat()
    
    if existing is not None:
        DATA_STORAGE[existing] = data
    else:
        DATA_STORAGE.append(data)
    
    return True

def get_all_data():
    """Ambil semua data"""
    return DATA_STORAGE

def clear_data():
    """Hapus semua data"""
    global DATA_STORAGE
    DATA_STORAGE = []
    return True

# ==================== KPJ GENERATOR ====================
def generate_kpj_list(base: str = None, count: int = 10) -> list:
    """Generate list KPJ (simulasi)"""
    kpj_list = []
    
    if base and len(base) >= 4:
        prefix = base[:4]
        suffix = base[4:] if len(base) > 4 else ""
    else:
        prefix = "2211"
        suffix = ""
    
    for i in range(count):
        # Format: prefix + 7 digit angka + suffix
        kpj = f"{prefix}{str(i).zfill(7)}{suffix}"[:11]
        kpj_list.append(kpj)
    
    return kpj_list

# ==================== HTML TEMPLATE ====================
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AutoCheck BPJS - Main Activity</title>
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
        
        .button-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 20px;
        }
        button {
            flex: 1;
            min-width: 100px;
            padding: 14px;
            font-size: 16px;
            font-weight: bold;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.2s;
        }
        button:hover { transform: translateY(-2px); }
        button:disabled { opacity: 0.6; transform: none; }
        
        .btn-check1 { background: #667eea; color: white; }
        .btn-check2 { background: #48bb78; color: white; }
        .btn-induk { background: #ed8936; color: white; }
        .btn-update { background: #e53e3e; color: white; }
        .btn-data { background: #805ad5; color: white; }
        .btn-generate { background: #38b2ac; color: white; }
        .btn-play { background: #48bb78; color: white; }
        .btn-stop { background: #e53e3e; color: white; }
        
        .status {
            text-align: center;
            padding: 10px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-weight: bold;
        }
        .status-success { background: #d4edda; color: #155724; }
        .status-error { background: #f8d7da; color: #721c24; }
        .status-warning { background: #fff3cd; color: #856404; }
        
        input {
            width: 100%;
            padding: 12px;
            font-size: 14px;
            border: 2px solid #ddd;
            border-radius: 10px;
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
        
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        td { padding: 8px; border-bottom: 1px solid #ddd; }
        td:first-child { font-weight: bold; width: 35%; background: #f0f0f0; }
        
        .progress {
            background: #e0e0e0;
            border-radius: 10px;
            height: 20px;
            margin: 10px 0;
            overflow: hidden;
        }
        .progress-bar {
            background: #48bb78;
            height: 100%;
            width: 0%;
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 11px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>🔍 AutoCheck BPJS</h1>
            <div class="sub">Automatic Check KPJ - POM & OSS</div>
            
            <div id="status" class="status status-warning">⏳ Siap</div>
            
            <div class="button-grid">
                <button class="btn-check1" onclick="checkPOM()">CHECK1 (POM)</button>
                <button class="btn-check2" onclick="checkOSS()">CHECK2 (OSS)</button>
                <button class="btn-induk" onclick="cariInduk()">INDUK</button>
                <button class="btn-update" onclick="updateData()">UPDATE</button>
                <button class="btn-data" onclick="lihatData()">DATA</button>
            </div>
            
            <div class="button-grid">
                <button class="btn-generate" onclick="generateKPJ()">⚙ GENERATE KPJ</button>
                <button class="btn-play" onclick="startAuto()">▶ PLAY</button>
                <button class="btn-stop" onclick="stopAuto()">⏹ STOP</button>
            </div>
            
            <div id="progress" class="progress" style="display: none;">
                <div id="progressBar" class="progress-bar">0%</div>
            </div>
            
            <input type="text" id="kpjInput" placeholder="Masukkan KPJ (11 digit) atau Base KPJ untuk generate" autocomplete="off">
            
            <div id="result" class="result">
                <h4>📊 Hasil</h4>
                <div id="resultContent"></div>
            </div>
            
            <div id="log" class="log">
                <p>📋 Sistem siap...</p>
            </div>
        </div>
    </div>

    <script>
        let isAutoRunning = false;
        let kpjList = [];
        let currentIndex = 0;
        
        function addLog(msg, isError = false) {
            const logDiv = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            const color = isError ? '#ff6b6b' : '#0f0';
            logDiv.innerHTML += `<p style="color: ${color}">[${time}] ${msg}</p>`;
            logDiv.scrollTop = logDiv.scrollHeight;
        }
        
        function updateStatus(message, type) {
            const statusDiv = document.getElementById('status');
            statusDiv.innerHTML = message;
            if (type === 'success') {
                statusDiv.className = 'status status-success';
            } else if (type === 'error') {
                statusDiv.className = 'status status-error';
            } else {
                statusDiv.className = 'status status-warning';
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
                            html += `<tr><td style="font-weight: bold">${key}</td><td>${escapeHtml(String(val))}</td></tr>`;
                        }
                    }
                    html += '</table>';
                }
                contentDiv.innerHTML = html;
            } else {
                contentDiv.innerHTML = `<div style="color: red">❌ ${escapeHtml(data.message || 'Error')}</div>`;
            }
            resultDiv.classList.add('show');
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        async function checkPOM() {
            const kpj = document.getElementById('kpjInput').value.trim();
            if (!kpj || !/^\\d{11}$/.test(kpj)) {
                alert('Masukkan KPJ 11 digit!');
                return;
            }
            
            addLog(`🔍 Check POM: ${kpj}`);
            updateStatus('Mengecek...', 'warning');
            
            try {
                const res = await fetch('/check-pom', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ kpj: kpj })
                });
                const data = await res.json();
                addLog(`Response: ${JSON.stringify(data)}`);
                showResult(data);
                updateStatus(data.status === 'SUCCESS' ? 'Data ditemukan' : 'Gagal', data.status === 'SUCCESS' ? 'success' : 'error');
            } catch (err) {
                addLog(`Error: ${err.message}`, true);
                updateStatus('Error', 'error');
            }
        }
        
        async function checkOSS() {
            const kpj = document.getElementById('kpjInput').value.trim();
            if (!kpj || !/^\\d{11}$/.test(kpj)) {
                alert('Masukkan KPJ 11 digit!');
                return;
            }
            
            addLog(`🔍 Check OSS: ${kpj}`);
            updateStatus('Mengecek OSS...', 'warning');
            
            try {
                const res = await fetch('/check-oss', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ kpj: kpj })
                });
                const data = await res.json();
                addLog(`Response: ${JSON.stringify(data)}`);
                showResult(data);
                updateStatus(data.status === 'SUCCESS' ? 'Data ditemukan' : 'Gagal', data.status === 'SUCCESS' ? 'success' : 'error');
            } catch (err) {
                addLog(`Error: ${err.message}`, true);
            }
        }
        
        async function cariInduk() {
            addLog(`🔍 Mencari induk KPJ...`);
            updateStatus('Mencari induk...', 'warning');
            
            try {
                const res = await fetch('/cari-induk', { method: 'POST' });
                const data = await res.json();
                addLog(`Response: ${JSON.stringify(data)}`);
                showResult(data);
                updateStatus('Selesai', 'success');
            } catch (err) {
                addLog(`Error: ${err.message}`, true);
            }
        }
        
        async function updateData() {
            const kpj = document.getElementById('kpjInput').value.trim();
            if (!kpj || !/^\\d{11}$/.test(kpj)) {
                alert('Masukkan KPJ 11 digit untuk update!');
                return;
            }
            
            addLog(`📝 Update data: ${kpj}`);
            updateStatus('Mengupdate...', 'warning');
            
            try {
                const res = await fetch('/update-data', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ kpj: kpj })
                });
                const data = await res.json();
                addLog(`Response: ${JSON.stringify(data)}`);
                showResult(data);
                updateStatus('Update selesai', 'success');
            } catch (err) {
                addLog(`Error: ${err.message}`, true);
            }
        }
        
        async function lihatData() {
            addLog(`📊 Mengambil data tersimpan...`);
            
            try {
                const res = await fetch('/data');
                const data = await res.json();
                addLog(`Total data: ${data.count || 0} record`);
                
                if (data.data && data.data.length > 0) {
                    let html = '<div class="success">✅ Data Tersimpan:</div>';
                    html += '<table>';
                    html += `<tr><th>KPJ</th><th>NIK</th><th>Nama</th></tr>`;
                    for (const item of data.data.slice(0, 20)) {
                        html += `<tr><td>${escapeHtml(item.kpj || '-')}</td><td>${escapeHtml(item.nik || '-')}</td><td>${escapeHtml(item.nama || '-')}</td></tr>`;
                    }
                    if (data.data.length > 20) {
                        html += `<tr><td colspan="3">... dan ${data.data.length - 20} data lainnya</td></tr>`;
                    }
                    html += '</table>';
                    document.getElementById('resultContent').innerHTML = html;
                    document.getElementById('result').classList.add('show');
                } else {
                    showResult({ status: 'ERROR', message: 'Belum ada data' });
                }
            } catch (err) {
                addLog(`Error: ${err.message}`, true);
            }
        }
        
        async function generateKPJ() {
            const base = document.getElementById('kpjInput').value.trim();
            addLog(`⚙ Generate KPJ dengan base: ${base || 'default'}`);
            
            try {
                const res = await fetch('/generate-kpj', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ base: base, count: 50 })
                });
                const data = await res.json();
                
                if (data.kpj_list) {
                    kpjList = data.kpj_list;
                    addLog(`✅ Generated ${kpjList.length} KPJ`);
                    document.getElementById('kpjInput').value = kpjList[0] || '';
                }
            } catch (err) {
                addLog(`Error: ${err.message}`, true);
            }
        }
        
        async function startAuto() {
            if (isAutoRunning) {
                addLog('Auto check sudah berjalan');
                return;
            }
            
            if (kpjList.length === 0) {
                await generateKPJ();
            }
            
            if (kpjList.length === 0) {
                addLog('Tidak ada KPJ untuk dicek', true);
                return;
            }
            
            isAutoRunning = true;
            currentIndex = 0;
            addLog(`▶ Memulai auto check, total ${kpjList.length} KPJ`);
            updateStatus('Auto check berjalan...', 'warning');
            document.getElementById('progress').style.display = 'block';
            
            while (isAutoRunning && currentIndex < kpjList.length) {
                const kpj = kpjList[currentIndex];
                const percent = Math.round((currentIndex / kpjList.length) * 100);
                document.getElementById('progressBar').style.width = `${percent}%`;
                document.getElementById('progressBar').innerHTML = `${percent}%`;
                
                addLog(`[${currentIndex + 1}/${kpjList.length}] Cek: ${kpj}`);
                
                try {
                    const res = await fetch('/check-pom', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ kpj: kpj })
                    });
                    const data = await res.json();
                    
                    if (data.status === 'SUCCESS') {
                        addLog(`✅ ${kpj} - Data ditemukan!`);
                        await fetch('/save-data', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(data.data)
                        });
                    } else {
                        addLog(`❌ ${kpj} - ${data.message}`);
                    }
                } catch (err) {
                    addLog(`❌ ${kpj} - Error: ${err.message}`, true);
                }
                
                currentIndex++;
                await new Promise(r => setTimeout(r, 3000));
            }
            
            isAutoRunning = false;
            document.getElementById('progress').style.display = 'none';
            addLog(`⏹ Auto check selesai. Terproses: ${currentIndex} KPJ`);
            updateStatus('Auto check selesai', 'success');
            await lihatData();
        }
        
        function stopAuto() {
            isAutoRunning = false;
            addLog(`⏹ Auto check dihentikan`);
            updateStatus('Auto check dihentikan', 'warning');
            document.getElementById('progress').style.display = 'none';
        }
    </script>
</body>
</html>
'''

# ==================== FLASK ROUTES ====================
scraper_pom = POMScraper()
scraper_oss = OSSScraper()


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/check-pom', methods=['POST'])
def check_pom():
    data = request.get_json()
    kpj = data.get('kpj', '').strip()
    
    if not kpj or len(kpj) != 11 or not kpj.isdigit():
        return jsonify({"status": "ERROR", "message": "KPJ harus 11 digit angka!"})
    
    result = scraper_pom.check_kpj(kpj)
    
    # Simpan retry count
    if result.get('status') == 'ERROR':
        retry = RETRY_COUNT.get(kpj, 0) + 1
        RETRY_COUNT[kpj] = retry
    
    return jsonify(result)


@app.route('/check-oss', methods=['POST'])
def check_oss():
    data = request.get_json()
    kpj = data.get('kpj', '').strip()
    
    if not kpj or len(kpj) != 11 or not kpj.isdigit():
        return jsonify({"status": "ERROR", "message": "KPJ harus 11 digit angka!"})
    
    result = scraper_oss.check_kpj(kpj)
    return jsonify(result)


@app.route('/cari-induk', methods=['POST'])
def cari_induk():
    """Cari induk KPJ pola random"""
    # Generate random KPJ patterns
    results = generate_kpj_list(count=20)
    return jsonify({"status": "SUCCESS", "data": {"induk_list": results, "message": "Berhasil generate induk KPJ"}})


@app.route('/update-data', methods=['POST'])
def update_data():
    data = request.get_json()
    kpj = data.get('kpj', '').strip()
    
    # Cek ulang KPJ dan update data
    result = scraper_pom.check_kpj(kpj)
    
    if result.get('status') == 'SUCCESS' and result.get('data'):
        save_data(result['data'])
        return jsonify({"status": "SUCCESS", "message": "Data berhasil diupdate", "data": result['data']})
    
    return jsonify({"status": "ERROR", "message": "Gagal update data"})


@app.route('/data', methods=['GET'])
def get_data():
    all_data = get_all_data()
    return jsonify({"status": "SUCCESS", "data": all_data, "count": len(all_data)})


@app.route('/save-data', methods=['POST'])
def save_data_route():
    data = request.get_json()
    if data:
        save_data(data)
        return jsonify({"status": "SUCCESS", "message": "Data tersimpan"})
    return jsonify({"status": "ERROR", "message": "No data"})


@app.route('/clear-data', methods=['POST'])
def clear_data_route():
    clear_data()
    return jsonify({"status": "SUCCESS", "message": "Semua data dihapus"})


@app.route('/generate-kpj', methods=['POST'])
def generate_kpj_route():
    data = request.get_json()
    base = data.get('base', '')
    count = min(data.get('count', 50), 500)
    
    kpj_list = generate_kpj_list(base, count)
    return jsonify({"status": "SUCCESS", "kpj_list": kpj_list, "count": len(kpj_list)})


@app.route('/login-pom', methods=['POST'])
def login_pom():
    result = scraper_pom.login()
    return jsonify(result)


@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "data_count": len(DATA_STORAGE),
        "retry_count": RETRY_COUNT,
        "pom_logged_in": scraper_pom.is_logged_in
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("="*50)
    print("🔍 AutoCheck BPJS - Main Activity")
    print("📱 Buka: http://localhost:{}".format(port))
    print("="*50)
    app.run(debug=False, host='0.0.0.0', port=port)
