from flask import Flask, request, jsonify, render_template_string
import requests
import re
import json
import os
import logging
import time
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

class POMDataScraper:
    def __init__(self):
        self.step3_url = "https://pom.bpjsketenagakerjaan.go.id/pu/step3"
        self.check_url = "https://pom.bpjsketenagakerjaan.go.id/pu/prosesPendaftaranTkKPJ"
        
        self.session = requests.Session()
        self.csrf_token = None
        self.is_logged_in = False
        self.last_request_time = 0
        self.min_delay = 2
        
        # Cookie dari aplikasi Android
        self.cookies = {
            'BIGipServerPOM_PUBLIK.app~POM_PUBLIK_pool': '!bzHFEKiCm9566ujniNkIKL0LQO8PDT4V1meh8znNFq7BIsYsOt/ZcmFPliFPJB9HfkzlFp1sGQYfR8L7J6aVmOmnu2uYZdbUxkHYRQ5Pog',
            'connect.sid': 's%3AbLZck55doqZOSYnKPmqFurPYbVysj9nK.koQyuuTttFJNg2vej7H22W9hVhKNA37JcpqnhckDm%2BE',
            '_csrf': 'HO4coKDS5PTPdSxyTwrCG8j7',
            'TS01859485': '011e8ab0a03d2392d5e5315c2ac48fb7e9f76294b4f900604d8951f0fdf256e45f08419bd1d3a9f41c86ce3b2137ec28cef6ab88926faef6d9f5f4d8e12396aa792f4b92e39dc8879dfa6b34c38afc79aa4ff099095a804e203a6f544279f1a2fe778dc209'
        }

    def _get_headers(self):
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'X-Requested-With': 'XMLHttpRequest',
        }

    def _wait(self):
        current_time = time.time()
        if current_time - self.last_request_time < self.min_delay:
            time.sleep(self.min_delay)
        self.last_request_time = time.time()

    def _extract_from_table(self, html):
        """Extract data dari tabel #datatable (seperti injectAmbilTK)"""
        data = {}
        
        # Cari tabel
        table_pattern = r'<table[^>]*id=["\']datatable["\'][^>]*>(.*?)</table>'
        table_match = re.search(table_pattern, html, re.DOTALL)
        
        if not table_match:
            return data
        
        table_html = table_match.group(1)
        
        # Ambil header
        header_pattern = r'<thead[^>]*>(.*?)</thead>'
        header_match = re.search(header_pattern, table_html, re.DOTALL)
        
        headers = []
        if header_match:
            th_pattern = r'<th[^>]*>(.*?)</th>'
            headers = re.findall(th_pattern, header_match.group(1), re.DOTALL)
            headers = [re.sub(r'<[^>]+>', '', h).strip() for h in headers]
        
        # Cari index kolom yang dibutuhkan
        idx_nik = -1
        idx_kpj = -1
        idx_nama = -1
        
        for i, h in enumerate(headers):
            h_lower = h.lower()
            if 'nomor identitas' in h_lower or 'nik' in h_lower:
                idx_nik = i
            elif 'kartu peserta' in h_lower or 'kpj' in h_lower:
                idx_kpj = i
            elif 'nama' in h_lower:
                idx_nama = i
        
        # Ambil baris data
        body_pattern = r'<tbody[^>]*>(.*?)</tbody>'
        body_match = re.search(body_pattern, table_html, re.DOTALL)
        
        if body_match:
            row_pattern = r'<tr[^>]*>(.*?)</tr>'
            rows = re.findall(row_pattern, body_match.group(1), re.DOTALL)
            
            for row in rows:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                cells_clean = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
                
                if len(cells_clean) > max(idx_nik, idx_kpj, idx_nama):
                    row_data = {}
                    for i, cell in enumerate(cells_clean):
                        if i < len(headers):
                            row_data[headers[i]] = cell
                    
                    # Simpan semua data
                    for key, val in row_data.items():
                        data[key] = val
        
        return data

    def check_kpj(self, kpj: str) -> dict:
        """Cek KPJ dan ambil data (NIK, Nama, Tanggal Lahir)"""
        logger.info(f"Mengecek KPJ: {kpj}")
        
        self._wait()
        
        try:
            headers = self._get_headers()
            
            # POST request ke endpoint check
            response = self.session.post(
                self.check_url,
                data={'kpj': kpj},
                headers=headers,
                cookies=self.cookies,
                timeout=60
            )
            
            logger.info(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    if data.get('ret') == '0':
                        logger.info("KPJ valid, mengambil data dari tabel...")
                        
                        # Ambil data dari step3
                        self._wait()
                        step3_response = self.session.get(
                            self.step3_url,
                            headers=headers,
                            cookies=self.cookies,
                            timeout=30
                        )
                        
                        if step3_response.status_code == 200:
                            table_data = self._extract_from_table(step3_response.text)
                            
                            # Format hasil
                            result = {
                                "status": "SUCCESS",
                                "message": "Data ditemukan!",
                                "data": {
                                    "nik": table_data.get('Nomor Identitas', ''),
                                    "nama": table_data.get('Nama', ''),
                                    "kpj": kpj,
                                    "tanggal_lahir": table_data.get('Tanggal Lahir', ''),
                                    "jenis_kelamin": table_data.get('Jenis Kelamin', ''),
                                    "alamat": table_data.get('Alamat', ''),
                                    "status": "VALID"
                                }
                            }
                            
                            # Coba ambil dari field lain jika kosong
                            if not result['data']['nik']:
                                for key, val in table_data.items():
                                    if 'nik' in key.lower():
                                        result['data']['nik'] = val
                                    elif 'nama' in key.lower():
                                        result['data']['nama'] = val
                                    elif 'tanggal' in key.lower() or 'tgl' in key.lower():
                                        result['data']['tanggal_lahir'] = val
                            
                            return result
                        else:
                            return {"status": "ERROR", "message": "Gagal mengambil halaman data"}
                    else:
                        return {"status": "ERROR", "message": data.get('msg', 'KPJ tidak valid')}
                        
                except json.JSONDecodeError:
                    return {"status": "ERROR", "message": "Response error"}
            else:
                return {"status": "ERROR", "message": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "ERROR", "message": str(e)}


scraper = POMDataScraper()


# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>POM BPJS - Ambil Data KPJ</title>
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
            background: white;
            border-radius: 20px;
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
        .status-green { background: #d4edda; color: #155724; }
        .status-red { background: #f8d7da; color: #721c24; }
        .status-yellow { background: #fff3cd; color: #856404; }
        
        input {
            width: 100%;
            padding: 14px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 10px;
            text-align: center;
            letter-spacing: 2px;
            margin-bottom: 15px;
        }
        
        button {
            width: 100%;
            padding: 14px;
            font-size: 16px;
            font-weight: bold;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
        }
        button:disabled { opacity: 0.6; cursor: not-allowed; }
        
        .result {
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
            display: none;
        }
        .result.show { display: block; }
        
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
        
        .success { background: #d4edda; color: #155724; padding: 10px; border-radius: 8px; margin-bottom: 15px; }
        .error { background: #f8d7da; color: #721c24; padding: 10px; border-radius: 8px; margin-bottom: 15px; }
        
        .log {
            background: #1a1a2e;
            color: #0f0;
            padding: 10px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 10px;
            max-height: 150px;
            overflow-y: auto;
            margin-top: 15px;
        }
        .log p { margin: 3px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 POM BPJS - Ambil Data KPJ</h1>
        <div class="sub">Ambil NIK, Nama, Tanggal Lahir, dll</div>
        
        <div id="status" class="status status-yellow">⏳ Siap</div>
        
        <input type="text" id="kpj" maxlength="11" placeholder="Masukkan KPJ (11 digit)" autocomplete="off">
        <button id="checkBtn" onclick="checkKPJ()">🔍 CEK & AMBIL DATA</button>
        
        <div id="result" class="result">
            <h4>📊 Hasil</h4>
            <div id="resultContent"></div>
        </div>
        
        <div id="log" class="log">
            <p>📋 Masukkan KPJ dan klik tombol di atas...</p>
        </div>
    </div>

    <script>
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
                statusDiv.className = 'status status-green';
            } else if (type === 'error') {
                statusDiv.className = 'status status-red';
            } else {
                statusDiv.className = 'status status-yellow';
            }
        }
        
        async function checkKPJ() {
            const kpj = document.getElementById('kpj').value.trim();
            const btn = document.getElementById('checkBtn');
            
            if (!kpj || !/^\\d{11}$/.test(kpj)) {
                alert('Masukkan KPJ 11 digit angka!');
                return;
            }
            
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
                
                if (data.status === 'SUCCESS') {
                    updateStatus('✅ Data ditemukan!', 'success');
                    
                    let html = '<div class="success">✅ Data Ditemukan!</div>';
                    html += '<table>';
                    
                    const fields = [
                        {key: 'nik', label: 'NIK'},
                        {key: 'nama', label: 'Nama'},
                        {key: 'kpj', label: 'KPJ'},
                        {key: 'tanggal_lahir', label: 'Tanggal Lahir'},
                        {key: 'jenis_kelamin', label: 'Jenis Kelamin'},
                        {key: 'alamat', label: 'Alamat'},
                        {key: 'status', label: 'Status'}
                    ];
                    
                    for (const field of fields) {
                        if (data.data[field.key]) {
                            html += `<td><td style="font-weight: bold">${field.label}</td><td>${escapeHtml(String(data.data[field.key]))}</td></tr>`;
                        }
                    }
                    
                    html += '\\u003c/table>';
                    document.getElementById('resultContent').innerHTML = html;
                    document.getElementById('result').classList.add('show');
                    addLog('✅ Data berhasil diambil');
                } else {
                    updateStatus('❌ ' + data.message, 'error');
                    document.getElementById('resultContent').innerHTML = `<div class="error">❌ ${escapeHtml(data.message)}</div>`;
                    document.getElementById('result').classList.add('show');
                    addLog(`❌ ${data.message}`, true);
                }
            } catch (err) {
                addLog(`❌ Error: ${err.message}`, true);
                updateStatus('Error: ' + err.message, 'error');
            } finally {
                btn.disabled = false;
                btn.innerHTML = '🔍 CEK & AMBIL DATA';
            }
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        document.getElementById('kpj').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') checkKPJ();
        });
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


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
    print("🔍 POM BPJS - Ambil Data KPJ")
    print(f"📱 Buka: http://localhost:{port}")
    print("="*50)
    app.run(debug=False, host='0.0.0.0', port=port)
