from flask import Flask, request, jsonify, render_template_string
import requests
import json
import os
import logging
import time
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class POMDataFinder:
    def __init__(self):
        # URL dari aplikasi Android
        self.step3_url = "https://pom.bpjsketenagakerjaan.go.id/pu/step3"
        # Endpoint yang benar (dari kode Android)
        self.check_url = "https://pom.bpjsketenagakerjaan.go.id/pu/prosesPendaftaranTkKPJ"
        
        self.session = requests.Session()
        
        # COOKIE SESSION YANG VALID (dari browser/Android)
        self.cookies = {
            'BIGipServerPOM_PUBLIK.app~POM_PUBLIK_pool': '!bzHFEKiCm9566ujniNkIKL0LQO8PDT4V1meh8znNFq7BIsYsOt/ZcmFPliFPJB9HfkzlFp1sGQYfR8L7J6aVmOmnu2uYZdbUxkHYRQ5Pog',
            'connect.sid': 's%3AVUIfl_td4CZ8KSFhG7D0uCw_xQ4CayLw.swa4SZgv5kgKM4wqoPn25Pk9n8psTd%2Bfvl8l64xb1nU',
            '_csrf': 'HO4coKDS5PTPdSxyTwrCG8j7',
            'TS01859485': '011e8ab0a054c9118e5b34144f9c46d632b8e416c91366b253434a891ef77f24ef69af885168098a11b4c208dd787181b5e76d7078896a78ffa814e5b07a6251b979f33765ed1617ea7e980441036bb53d8c8c359a4abbbfc7962dadf10393e5a5187096a3'
        }
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': self.step3_url,
            'Origin': 'https://pom.bpjsketenagakerjaan.go.id',
            'X-Requested-With': 'XMLHttpRequest',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
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
        """
        Cari data berdasarkan KPJ
        Menggunakan endpoint yang sama dengan aplikasi Android:
        /pu/prosesPendaftaranTkKPJ
        """
        logger.info(f"Mencari data KPJ: {kpj} (percobaan ke-{retry+1})")
        
        if not self.is_connected:
            test = self.test_connection()
            if test['status'] != 'SUCCESS':
                return test
        
        try:
            # Siapkan payload (sama seperti di Android)
            payload = f'kpj={kpj}'
            
            logger.info(f"POST ke: {self.check_url}")
            logger.info(f"Payload: {payload}")
            
            response = self.session.post(
                self.check_url, 
                data=payload, 
                headers=self.headers, 
                cookies=self.cookies,
                timeout=60
            )
            
            logger.info(f"Response Status: {response.status_code}")
            logger.info(f"Response Body: {response.text[:500]}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Cek response ret code (sama seperti di Android)
                    if data.get('ret') == '0':
                        logger.info("✅ KPJ valid! Mengambil data...")
                        
                        # Jika sukses, kita perlu mengambil data dari halaman berikutnya
                        # Atau jika data sudah ada di response, langsung ambil
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
                            # Jika data tidak ada di response, ambil dari halaman step3
                            return self._ambil_data_dari_halaman(kpj)
                    
                    elif data.get('ret') == '-2':
                        return {"status": "ERROR", "message": "Klaim Penuh - KPJ sudah pernah diklaim"}
                    
                    elif data.get('ret') == '-1':
                        return {"status": "ERROR", "message": data.get('msg', 'Terjadi kesalahan')}
                    
                    else:
                        return {"status": "ERROR", "message": data.get('msg', 'KPJ tidak valid atau tidak ditemukan')}
                        
                except json.JSONDecodeError:
                    logger.warning(f"Response bukan JSON: {response.text[:200]}")
                    
                    # Cek apakah response mengandung pesan sukses
                    if 'success' in response.text.lower() or 'berhasil' in response.text.lower():
                        return self._ambil_data_dari_halaman(kpj)
                    
                    return {"status": "ERROR", "message": f"Response bukan JSON: {response.text[:100]}"}
            else:
                return {"status": "ERROR", "message": f"HTTP {response.status_code}"}
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout untuk KPJ: {kpj}")
            if retry < 2:
                time.sleep(3)
                return self.cari_data(kpj, retry + 1)
            return {"status": "ERROR", "message": "Request timeout setelah 3 kali percobaan"}
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "ERROR", "message": str(e)}

    def _ambil_data_dari_halaman(self, kpj: str) -> dict:
        """
        Ambil data dari halaman step3 setelah KPJ berhasil divalidasi
        Menggunakan metode seperti di aplikasi Android (injectAmbilTK)
        """
        logger.info(f"Mengambil data dari halaman untuk KPJ: {kpj}")
        
        try:
            # Ambil halaman step3
            response = self.session.get(self.step3_url, headers=self.headers, cookies=self.cookies, timeout=30)
            
            if response.status_code != 200:
                return {"status": "ERROR", "message": "Gagal mengambil halaman data"}
            
            html = response.text
            
            # Extract data dari tabel (seperti di Android)
            # Cari tabel dengan id 'datatable'
            table_pattern = r'<table[^>]*id=["\']datatable["\'][^>]*>(.*?)</table>'
            table_match = re.search(table_pattern, html, re.DOTALL)
            
            if not table_match:
                return {"status": "ERROR", "message": "Tabel data tidak ditemukan"}
            
            table_html = table_match.group(1)
            
            # Cari baris yang mengandung KPJ
            row_pattern = r'<tr[^>]*>(.*?)</tr>'
            rows = re.findall(row_pattern, table_html, re.DOTALL)
            
            # Cari header untuk mengetahui index kolom
            headers = []
            if rows:
                header_row = rows[0]
                header_pattern = r'<th[^>]*>(.*?)</th>'
                headers = re.findall(header_pattern, header_row, re.DOTALL)
                headers = [re.sub(r'<[^>]+>', '', h).strip() for h in headers]
            
            # Cari index kolom yang dibutuhkan
            idx_nik = -1
            idx_kpj = -1
            idx_nama = -1
            
            for i, h in enumerate(headers):
                h_lower = h.lower()
                if 'nomor identitas' in h_lower or 'nik' in h_lower:
                    idx_nik = i
                elif 'no kartu peserta' in h_lower or 'kpj' in h_lower:
                    idx_kpj = i
                elif 'nama' in h_lower:
                    idx_nama = i
            
            # Jika header tidak ditemukan, coba dengan posisi default
            if idx_kpj == -1:
                idx_kpj = 1  # asumsi kolom ke-2
            if idx_nik == -1:
                idx_nik = 0  # asumsi kolom ke-1
            if idx_nama == -1:
                idx_nama = 2  # asumsi kolom ke-3
            
            # Cari data di baris data (mulai dari baris ke-2)
            for row in rows[1:]:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                if len(cells) <= max(idx_kpj, idx_nik, idx_nama):
                    continue
                
                # Bersihkan cell dari tag HTML
                cells_clean = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
                
                if idx_kpj < len(cells_clean) and cells_clean[idx_kpj] == kpj:
                    # Data ditemukan
                    personal = {
                        "nik": cells_clean[idx_nik] if idx_nik < len(cells_clean) else "",
                        "kpj": cells_clean[idx_kpj] if idx_kpj < len(cells_clean) else "",
                        "nama": cells_clean[idx_nama] if idx_nama < len(cells_clean) else "",
                    }
                    
                    # Cari field tambahan
                    field_labels = ['upah', 'gaji', 'tanggal_lahir', 'tgl_lahir', 'jenis_kelamin', 'status_kawin', 'alamat']
                    for i, cell in enumerate(cells_clean):
                        if i < len(headers):
                            header_lower = headers[i].lower()
                            if 'upah' in header_lower or 'gaji' in header_lower:
                                personal['gaji'] = cell
                            elif 'tanggal' in header_lower or 'tgl' in header_lower:
                                personal['tanggal_lahir'] = cell
                            elif 'jenis' in header_lower or 'kelamin' in header_lower:
                                personal['jenis_kelamin'] = cell
                            elif 'kawin' in header_lower or 'status' in header_lower:
                                personal['status_kawin'] = cell
                            elif 'alamat' in header_lower:
                                personal['alamat'] = cell
                    
                    return {
                        "status": "SUCCESS",
                        "message": "Data ditemukan!",
                        "data": personal
                    }
            
            return {"status": "ERROR", "message": f"Data dengan KPJ {kpj} tidak ditemukan di tabel"}
            
        except Exception as e:
            logger.error(f"Error mengambil data: {e}")
            return {"status": "ERROR", "message": str(e)}


# Inisialisasi
finder = POMDataFinder()


# HTML Template (sama seperti sebelumnya)
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
        .cookie-info {
            background: #e7f3ff;
            padding: 10px;
            border-radius: 8px;
            font-size: 11px;
            word-break: break-all;
            margin-top: 15px;
        }
        .cookie-info summary { cursor: pointer; font-weight: bold; color: #0066cc; }
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
                    'alamat': 'Alamat'
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
                html += '</table>';
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
                } else if (data.message && data.message.includes('timeout')) {
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
