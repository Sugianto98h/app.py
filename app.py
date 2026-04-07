from flask import Flask, request, jsonify, render_template_string
import requests
import json
import os
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class POMDataFinder:
    def __init__(self):
        self.step3_url = "https://pom.bpjsketenagakerjaan.go.id/pu/step3"
        self.check_url = "https://pom.bpjsketenagakerjaan.go.id/pu/prosesHapusTkAll"
        
        self.session = requests.Session()
        
        # COOKIE SESSION YANG VALID
        self.cookies = {
            'BIGipServerPOM_PUBLIK.app~POM_PUBLIK_pool': '!bzHFEKiCm9566ujniNkIKL0LQO8PDT4V1meh8znNFq7BIsYsOt/ZcmFPliFPJB9HfkzlFp1sGQYfR8L7J6aVmOmnu2uYZdbUxkHYRQ5Pog',
            'connect.sid': 's%3AVUIfl_td4CZ8KSFhG7D0uCw_xQ4CayLw.swa4SZgv5kgKM4wqoPn25Pk9n8psTd%2Bfvl8l64xb1nU',
            '_csrf': 'HO4coKDS5PTPdSxyTwrCG8j7',
            'TS01859485': '011e8ab0a054c9118e5b34144f9c46d632b8e416c91366b253434a891ef77f24ef69af885168098a11b4c208dd787181b5e76d7078896a78ffa814e5b07a6251b979f33765ed1617ea7e980441036bb53d8c8c359a4abbbfc7962dadf10393e5a5187096a3'
        }
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': self.step3_url,
            'Origin': 'https://pom.bpjsketenagakerjaan.go.id',
            'X-Requested-With': 'XMLHttpRequest',
            'Connection': 'keep-alive',
        }
        
        self.is_connected = False

    def test_connection(self) -> dict:
        """Test koneksi dengan cookie yang ada"""
        logger.info("Menguji koneksi ke POM...")
        
        try:
            response = self.session.get(self.step3_url, headers=self.headers, cookies=self.cookies, timeout=30)
            
            logger.info(f"Step3 Status: {response.status_code}")
            
            if response.status_code == 200:
                if response.text.startswith('{'):
                    try:
                        data = response.json()
                        if data.get('ret') == '-1':
                            return {"status": "ERROR", "message": f"Session tidak valid: {data.get('msg')}"}
                    except:
                        pass
                
                self.is_connected = True
                return {"status": "SUCCESS", "message": "Terhubung ke POM dengan cookie valid!"}
            else:
                return {"status": "ERROR", "message": f"Gagal akses step3 (HTTP {response.status_code})"}
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "ERROR", "message": str(e)}

    def cari_data(self, kpj: str, retry: int = 0) -> dict:
        """Cari data berdasarkan KPJ dengan retry mechanism"""
        logger.info(f"Mencari data KPJ: {kpj} (percobaan ke-{retry+1})")
        
        if not self.is_connected:
            test = self.test_connection()
            if test['status'] != 'SUCCESS':
                return test
        
        try:
            # Siapkan payload
            payload = {'kpj': kpj}
            
            # Timeout lebih panjang (60 detik)
            response = self.session.post(
                self.check_url, 
                data=payload, 
                headers=self.headers, 
                cookies=self.cookies,
                timeout=60
            )
            
            logger.info(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    if data.get('ret') == '0':
                        result_data = data.get('data', [])
                        
                        if result_data and len(result_data) > 0:
                            personal = result_data[0]
                            return {
                                "status": "SUCCESS",
                                "message": "Data ditemukan!",
                                "data": personal,
                                "raw": data
                            }
                        else:
                            return {"status": "ERROR", "message": "Data kosong"}
                    else:
                        return {"status": "ERROR", "message": data.get('msg', 'KPJ tidak valid atau tidak ditemukan')}
                        
                except json.JSONDecodeError:
                    return {"status": "ERROR", "message": f"Response bukan JSON: {response.text[:100]}"}
            else:
                return {"status": "ERROR", "message": f"HTTP {response.status_code}"}
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout untuk KPJ: {kpj}")
            if retry < 2:  # Maksimal 3 percobaan
                time.sleep(3)  # Tunggu 3 detik sebelum retry
                return self.cari_data(kpj, retry + 1)
            return {"status": "ERROR", "message": "Request timeout setelah 3 kali percobaan. Server POM lambat merespon."}
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "ERROR", "message": str(e)}


# Inisialisasi
finder = POMDataFinder()


# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>POM BPJS - Cari Data KPJ</title>
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
        .btn-test { background: #28a745; color: white; }
        .btn-search { background: #667eea; color: white; }
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
        .warning { background: #fff3cd; color: #856404; padding: 10px; border-radius: 8px; margin-bottom: 15px; }
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
        .cookie-info {
            background: #e7f3ff;
            padding: 10px;
            border-radius: 8px;
            font-size: 11px;
            word-break: break-all;
            margin-top: 15px;
        }
        .cookie-info summary {
            cursor: pointer;
            font-weight: bold;
            color: #0066cc;
        }
        .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-left: 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>🔍 POM BPJS - Cari Data KPJ</h1>
            <div class="sub">Cari data peserta berdasarkan Nomor KPJ</div>
            
            <div id="status" class="status status-yellow">⏳ Belum diuji</div>
            
            <button id="testBtn" class="btn-test" onclick="doTest()">🔌 UJI KONEKSI</button>
            
            <hr>
            
            <h3 style="margin-bottom: 15px;">📝 Cari Data KPJ</h3>
            <input type="text" id="kpj" maxlength="11" placeholder="Masukkan KPJ (11 digit)" autocomplete="off">
            <button id="searchBtn" class="btn-search" onclick="doSearch()" disabled>🔍 CARI DATA</button>
            
            <div id="result" class="result">
                <h4>📊 Hasil Pencarian</h4>
                <div id="resultContent"></div>
            </div>
            
            <div id="log" class="log">
                <p>📋 Klik tombol "UJI KONEKSI" untuk mulai...</p>
                <p>⚠️ Server POM kadang lambat, bisa sampai 60 detik.</p>
            </div>
            
            <details class="cookie-info">
                <summary>🔐 Cookie Session (Tersimpan di Kode)</summary>
                <p style="margin-top: 8px;">✅ BIGipServerPOM_PUBLIK_pool<br>✅ connect.sid<br>✅ _csrf<br>✅ TS01859485</p>
            </details>
        </div>
    </div>

    <script>
        let isConnected = false;
        let isSearching = false;
        
        function addLog(msg, isError = false, isWarning = false) {
            const logDiv = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            let color = '#0f0';
            if (isError) color = '#ff6b6b';
            if (isWarning) color = '#ffaa00';
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
        
        function showResult(type, content, data = null) {
            const resultDiv = document.getElementById('result');
            const contentDiv = document.getElementById('resultContent');
            
            if (type === 'success' && data) {
                let html = '<div class="success">✅ Data Ditemukan!</div>';
                html += '<table>';
                
                const fieldLabels = {
                    'nik': 'NIK',
                    'nomorIdentitas': 'NIK',
                    'namaLengkap': 'Nama Lengkap',
                    'nama': 'Nama',
                    'kpj': 'KPJ',
                    'nomUpah': 'Gaji / Upah',
                    'gaji': 'Gaji',
                    'tanggalLahir': 'Tanggal Lahir',
                    'tglLahir': 'Tanggal Lahir',
                    'jenisKelamin': 'Jenis Kelamin',
                    'statusKawin': 'Status Kawin',
                    'alamat': 'Alamat',
                    'kodePos': 'Kode Pos',
                    'hp': 'Nomor HP',
                    'email': 'Email'
                };
                
                let found = false;
                for (const [key, value] of Object.entries(data)) {
                    if (fieldLabels[key] || key.toLowerCase().includes('nama') || key.toLowerCase().includes('nik') || key.toLowerCase().includes('kpj')) {
                        found = true;
                        const label = fieldLabels[key] || key;
                        html += `<tr><td style="font-weight: bold">${label}</td><td>${escapeHtml(String(value))}</td></tr>`;
                    }
                }
                
                if (!found) {
                    html += `<tr><td colspan="2">${escapeHtml(JSON.stringify(data, null, 2))}</td></tr>`;
                }
                html += '\\u003c/table>';
                contentDiv.innerHTML = html;
            } else if (type === 'success') {
                contentDiv.innerHTML = `<div class="success">✅ ${escapeHtml(content)}</div>`;
            } else if (type === 'warning') {
                contentDiv.innerHTML = `<div class="warning">⚠️ ${escapeHtml(content)}</div>`;
            } else {
                contentDiv.innerHTML = `<div class="error">❌ ${escapeHtml(content)}</div>`;
            }
            
            resultDiv.classList.add('show');
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        async function doTest() {
            const btn = document.getElementById('testBtn');
            const searchBtn = document.getElementById('searchBtn');
            
            btn.disabled = true;
            updateStatus('Menguji koneksi...', 'loading');
            addLog('🚀 Menguji koneksi ke POM dengan cookie...');
            
            try {
                const res = await fetch('/test', { method: 'POST' });
                const data = await res.json();
                addLog(`Response: ${JSON.stringify(data)}`);
                
                if (data.status === 'SUCCESS') {
                    isConnected = true;
                    updateStatus('✅ Terhubung ke POM!', 'success');
                    searchBtn.disabled = false;
                    showResult('success', data.message);
                    addLog('✅ Koneksi berhasil! Cookie valid.');
                } else {
                    updateStatus('❌ Gagal terhubung', 'error');
                    showResult('error', data.message);
                    addLog(`❌ Gagal: ${data.message}`, true);
                }
            } catch (err) {
                addLog(`❌ Error: ${err.message}`, true);
                updateStatus('Error: ' + err.message, 'error');
                showResult('error', err.message);
            } finally {
                btn.disabled = false;
            }
        }
        
        async function doSearch() {
            if (!isConnected) {
                alert('Uji koneksi dulu!');
                return;
            }
            
            if (isSearching) {
                addLog('⏳ Masih dalam proses pencarian...', false, true);
                return;
            }
            
            const kpj = document.getElementById('kpj').value.trim();
            if (!kpj || !/^\\d{11}$/.test(kpj)) {
                alert('Masukkan KPJ yang valid (11 digit angka)!');
                return;
            }
            
            const btn = document.getElementById('searchBtn');
            isSearching = true;
            btn.disabled = true;
            btn.innerHTML = '⏳ MENCARI... (maks 60 detik)';
            updateStatus('Mencari data... (server POM lambat, harap tunggu)', 'loading');
            addLog(`🔍 Mencari data KPJ: ${kpj} (timeout 60 detik, akan retry jika timeout)`);
            
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 65000);
                
                const res = await fetch('/cari', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ kpj: kpj }),
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                const data = await res.json();
                addLog(`Response: ${JSON.stringify(data)}`);
                
                if (data.status === 'SUCCESS') {
                    updateStatus('✅ Data ditemukan!', 'success');
                    showResult('success', 'Data ditemukan!', data.data);
                    addLog('✅ Data berhasil ditemukan');
                } else if (data.message.includes('timeout')) {
                    updateStatus('⚠️ Timeout - Server lambat', 'error');
                    showResult('warning', data.message);
                    addLog(`⚠️ ${data.message}`, false, true);
                } else {
                    updateStatus('❌ Data tidak ditemukan', 'error');
                    showResult('error', data.message);
                    addLog(`❌ ${data.message}`, true);
                }
            } catch (err) {
                if (err.name === 'AbortError') {
                    addLog('⏰ Request dibatalkan karena timeout (65 detik)', true);
                    showResult('warning', 'Request timeout. Server POM sangat lambat. Coba lagi nanti.');
                } else {
                    addLog(`❌ Error: ${err.message}`, true);
                    showResult('error', err.message);
                }
            } finally {
                isSearching = false;
                btn.disabled = false;
                btn.innerHTML = '🔍 CARI DATA';
            }
        }
        
        document.getElementById('kpj').addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && isConnected && !isSearching) doSearch();
        });
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/test', methods=['POST'])
def test():
    result = finder.test_connection()
    return jsonify(result)


@app.route('/cari', methods=['POST'])
def cari():
    data = request.get_json()
    kpj = data.get('kpj', '').strip()
    
    if not kpj or len(kpj) != 11 or not kpj.isdigit():
        return jsonify({"status": "ERROR", "message": "KPJ harus 11 digit angka!"})
    
    result = finder.cari_data(kpj)
    return jsonify(result)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("="*50)
    print("🔍 POM BPJS - Cari Data KPJ")
    print(f"📱 Buka: http://localhost:{port}")
    print("⚠️  Server POM kadang lambat, timeout diatur 60 detik")
    print("="*50)
    app.run(debug=False, host='0.0.0.0', port=port)
