from flask import Flask, render_template, request, jsonify
import requests
import re
import json

app = Flask(__name__)

class POMScraperWithToken:
    def __init__(self):
        # TOKEN PERSIS SEPERTI YANG DIBERIKAN - TIDAK DIUBAH
        self.token = "2d6f.5380c38bfab80c4f/d90443d0-2cee-11f1-a839-525400cbcb5e/d19140869f7db161ebe006743ce23f8b4b5b7fb2/2?e=tGdHzLA2427rjrQ2UU6emUWS%2FgKC2z2XSHOblwKa%2Bp%2BCPcx8x7h7BnOqq7YgWTqrV57WXvtRjGLRsSWlP1%2F1XChzwE7VbnOfSXQNdnhAL0q3Qlhv8Gcz7EFZCyaZFRPnjAE%2Bd9XZTupbrMhpjRIpXl4PoNdI8Iqm%2F2kLWLh08gfy2VEkhJs2F2QfqB%2ByP%2BzX"
        
        self.base_url = "https://pom.bpjsketenagakerjaan.go.id"
        self.session = requests.Session()
        self.csrf_token = None
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/html, */*',
            'Referer': f'{self.base_url}/pu/step3',
            'X-Token': self.token,
            'Authorization': f'Bearer {self.token}',
            'Cookie': f'token={self.token}',
            'Token': self.token,
        }

    def connect_to_pom(self) -> bool:
        try:
            response = self.session.get(
                f'{self.base_url}/pu/step3', 
                headers=self.headers, 
                timeout=30
            )
            
            if response.status_code == 200:
                csrf_pattern = r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']'
                match = re.search(csrf_pattern, response.text)
                
                if match:
                    self.csrf_token = match.group(1)
                    self.headers['Cookie'] = f'_csrf={self.csrf_token}; token={self.token}'
                
                return True
            return False
        except Exception as e:
            print(f"Error: {e}")
            return False

    def check_kpj(self, kpj: str) -> dict:
        if not self.csrf_token:
            return {"status": "ERROR", "message": "Not connected to POM"}
        
        try:
            payload = {'kpj': kpj, '_csrf': self.csrf_token}
            headers = {**self.headers, 'X-Requested-With': 'XMLHttpRequest'}
            
            response = self.session.post(
                f'{self.base_url}/pu/prosesHapusTkAll',
                data=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                try:
                    return {"status": "SUCCESS", "data": response.json()}
                except:
                    return {"status": "HTML", "data": response.text[:500]}
            else:
                return {"status": "ERROR", "http_code": response.status_code, "response": response.text[:200]}
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}


scraper = POMScraperWithToken()
scraper.connect_to_pom()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/check', methods=['POST'])
def check_kpj():
    data = request.get_json()
    kpj = data.get('kpj', '').strip()
    
    if not kpj or len(kpj) != 11 or not kpj.isdigit():
        return jsonify({"status": "ERROR", "message": "KPJ harus 11 digit angka!"})
    
    result = scraper.check_kpj(kpj)
    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)            transition: all 0.3s;
            text-align: center;
            letter-spacing: 2px;
        }

        input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 10px rgba(102,126,234,0.3);
        }

        button {
            width: 100%;
            padding: 15px;
            font-size: 18px;
            font-weight: bold;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: transform 0.2s;
        }

        button:hover {
            transform: translateY(-2px);
        }

        button:disabled {
            opacity: 0.6;
            transform: none;
            cursor: not-allowed;
        }

        .result {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            display: none;
        }

        .result.show {
            display: block;
            animation: fadeIn 0.5s;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .result h3 {
            margin-bottom: 15px;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }

        .result pre {
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            font-size: 12px;
            font-family: 'Courier New', monospace;
        }

        .status-badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 15px;
        }

        .status-success {
            background: #d4edda;
            color: #155724;
        }

        .status-error {
            background: #f8d7da;
            color: #721c24;
        }

        .info-token {
            background: #e7f3ff;
            padding: 10px;
            border-radius: 8px;
            font-size: 11px;
            color: #0066cc;
            margin-top: 20px;
            word-break: break-all;
        }

        .loading {
            display: none;
            text-align: center;
            margin-top: 20px;
        }

        .loading.show {
            display: block;
        }

        .spinner {
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 15px;
        }

        .data-table {
            width: 100%;
            border-collapse: collapse;
        }

        .data-table td {
            padding: 10px;
            border-bottom: 1px solid #e0e0e0;
        }

        .data-table td:first-child {
            font-weight: bold;
            width: 35%;
            background: #f0f0f0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏦 POM BPJS Scraper</h1>
            <p>Cek Data Peserta BPJS Ketenagakerjaan via POM</p>
        </div>
        
        <div class="content">
            <div class="form-group">
                <label>📝 Nomor KPJ (11 digit)</label>
                <input type="text" id="kpj" maxlength="11" placeholder="Contoh: 12345678901" autocomplete="off">
            </div>
            
            <button id="checkBtn" onclick="checkKPJ()">🔍 CHECK</button>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p style="margin-top: 10px;">Memproses data...</p>
            </div>
            
            <div class="result" id="result">
                <h3>📊 Hasil Pengecekan</h3>
                <div id="resultContent"></div>
            </div>
            
            <div class="info-token">
                <strong>🔑 Token terhubung:</strong><br>
                {{ token_preview }}
            </div>
        </div>
    </div>

    <script>
        async function checkKPJ() {
            const kpj = document.getElementById('kpj').value.trim();
            const checkBtn = document.getElementById('checkBtn');
            const loading = document.getElementById('loading');
            const resultDiv = document.getElementById('result');
            const resultContent = document.getElementById('resultContent');
            
            // Validasi
            if (!kpj) {
                showError('Masukkan nomor KPJ!');
                return;
            }
            
            if (!/^\d{11}$/.test(kpj)) {
                showError('KPJ harus 11 digit angka!');
                return;
            }
            
            // Show loading
            checkBtn.disabled = true;
            loading.classList.add('show');
            resultDiv.classList.remove('show');
            
            try {
                const response = await fetch('/check', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ kpj: kpj })
                });
                
                const data = await response.json();
                
                if (data.status === 'SUCCESS') {
                    displaySuccess(data.data);
                } else if (data.status === 'HTML') {
                    displayHTML(data.data);
                } else {
                    displayError(data.message || data.response || 'Terjadi kesalahan');
                }
                
            } catch (error) {
                displayError('Network error: ' + error.message);
            } finally {
                checkBtn.disabled = false;
                loading.classList.remove('show');
                resultDiv.classList.add('show');
            }
        }
        
        function showError(message) {
            const resultContent = document.getElementById('resultContent');
            const resultDiv = document.getElementById('result');
            resultContent.innerHTML = `<div class="error-message">⚠️ ${message}</div>`;
            resultDiv.classList.add('show');
        }
        
        function displaySuccess(data) {
            const resultContent = document.getElementById('resultContent');
            
            let html = '<span class="status-badge status-success">✅ SUKSES</span>';
            
            if (data.data && typeof data.data === 'object') {
                html += '<table class="data-table">';
                for (const [key, value] of Object.entries(data.data)) {
                    let displayValue = value;
                    if (typeof value === 'object') {
                        displayValue = JSON.stringify(value);
                    }
                    html += `<tr><td>${key}</td><td>${escapeHtml(String(displayValue))}</td></tr>`;
                }
                html += '</table>';
            } else {
                html += `<pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
            }
            
            resultContent.innerHTML = html;
        }
        
        function displayHTML(html) {
            const resultContent = document.getElementById('resultContent');
            resultContent.innerHTML = `
                <span class="status-badge status-success">📄 HTML RESPONSE</span>
                <pre>${escapeHtml(html)}</pre>
            `;
        }
        
        function displayError(message) {
            const resultContent = document.getElementById('resultContent');
            resultContent.innerHTML = `
                <span class="status-badge status-error">❌ ERROR</span>
                <div class="error-message">${escapeHtml(message)}</div>
            `;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Enter key support
        document.getElementById('kpj').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                checkKPJ();
            }
        });
    </script>
</body>
</html>
