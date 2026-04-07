from flask import Flask, request, jsonify, render_template_string
import requests
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class POMBot:
    def __init__(self):
        self.token_url = "https://pom.bpjsketenagakerjaan.go.id/pu/login?t=YTliOWM0OGNjMGExYWVlOTUyZGU2YTg5MjExNDk0YmFkYWZhOTQ0MzJkODZmZGUwYTY5OTNjMTUwMDI4MzIjMQ=="
        self.step3_url = "https://pom.bpjsketenagakerjaan.go.id/pu/step3"
        self.session = requests.Session()
        self.token_opened = False
        self.step3_opened = False
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
        }

    def buka_token(self) -> dict:
        """Tugas 1: Buka token URL"""
        logger.info("="*50)
        logger.info("TUGAS 1: Membuka token URL...")
        logger.info(f"URL: {self.token_url}")
        
        try:
            response = self.session.get(self.token_url, headers=self.headers, timeout=30, allow_redirects=True)
            
            logger.info(f"Status: {response.status_code}")
            logger.info(f"Final URL: {response.url}")
            
            if response.status_code == 200:
                self.token_opened = True
                return {"status": "SUCCESS", "message": "Token berhasil dibuka!", "final_url": response.url}
            else:
                return {"status": "ERROR", "message": f"Token gagal dibuka (HTTP {response.status_code})", "final_url": response.url}
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "ERROR", "message": str(e)}

    def buka_step3(self) -> dict:
        """Tugas 2: Buka step3"""
        logger.info("="*50)
        logger.info("TUGAS 2: Membuka step3...")
        logger.info(f"URL: {self.step3_url}")
        
        try:
            response = self.session.get(self.step3_url, headers=self.headers, timeout=30)
            
            logger.info(f"Status: {response.status_code}")
            logger.info(f"Response: {response.text[:200]}")
            
            if response.status_code == 200:
                self.step3_opened = True
                return {"status": "SUCCESS", "message": "Step3 berhasil dibuka!", "response": response.text[:500]}
            else:
                return {"status": "ERROR", "message": f"Step3 gagal dibuka (HTTP {response.status_code})", "response": response.text[:200]}
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "ERROR", "message": str(e)}


bot = POMBot()


# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>POM BPJS - Token Opener</title>
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
        .btn-token { background: #28a745; color: white; }
        .btn-step3 { background: #17a2b8; color: white; }
        button:disabled { opacity: 0.6; cursor: not-allowed; }
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
            max-height: 200px;
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
            margin-top: 15px;
        }
        .log p { margin: 3px 0; }
        hr {
            margin: 20px 0;
            border: none;
            border-top: 1px solid #ddd;
        }
        .iframe-container {
            margin-top: 20px;
            border: 1px solid #ddd;
            border-radius: 10px;
            overflow: hidden;
        }
        iframe {
            width: 100%;
            height: 400px;
            border: none;
        }
        .link-info {
            font-size: 11px;
            color: #666;
            word-break: break-all;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>🏦 POM BPJS Opener</h1>
            <div class="sub">Buka Token → Buka Step3</div>
            
            <div id="statusToken" class="status status-red">❌ Token: Belum dibuka</div>
            <div id="statusStep3" class="status status-red">❌ Step3: Belum dibuka</div>
            
            <button id="tokenBtn" class="btn-token" onclick="bukaToken()">1️⃣ BUKA TOKEN</button>
            <button id="step3Btn" class="btn-step3" onclick="bukaStep3()" disabled>2️⃣ BUKA STEP3</button>
            
            <div id="result" class="result">
                <h4>📋 Hasil</h4>
                <div id="resultContent"></div>
            </div>
            
            <div id="log" class="log">
                <p>📋 Klik tombol di atas...</p>
            </div>
        </div>
        
        <!-- Jika token berhasil, tampilkan iframe step3 -->
        <div id="iframeContainer" class="card" style="display: none;">
            <h3>🌐 Halaman Step3</h3>
            <div class="iframe-container">
                <iframe id="step3Frame" src="about:blank"></iframe>
            </div>
            <div class="link-info" id="step3Url"></div>
        </div>
    </div>

    <script>
        let tokenOpened = false;
        
        function addLog(msg, isError = false) {
            const logDiv = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            const color = isError ? '#ff6b6b' : '#0f0';
            logDiv.innerHTML += `<p style="color: ${color}">[${time}] ${msg}</p>`;
            logDiv.scrollTop = logDiv.scrollHeight;
        }
        
        function updateStatus(elementId, message, isSuccess) {
            const el = document.getElementById(elementId);
            if (isSuccess) {
                el.innerHTML = '✅ ' + message;
                el.className = 'status status-green';
            } else {
                el.innerHTML = '❌ ' + message;
                el.className = 'status status-red';
            }
        }
        
        function showResult(type, content) {
            const resultDiv = document.getElementById('result');
            const contentDiv = document.getElementById('resultContent');
            
            if (type === 'success') {
                contentDiv.innerHTML = `<div class="success">✅ ${content}</div>`;
            } else {
                contentDiv.innerHTML = `<div class="error">❌ ${content}</div>`;
            }
            resultDiv.classList.add('show');
        }
        
        async function bukaToken() {
            const btn = document.getElementById('tokenBtn');
            const step3Btn = document.getElementById('step3Btn');
            
            btn.disabled = true;
            updateStatus('statusToken', 'Membuka token...', false);
            addLog('🚀 Membuka token URL...');
            
            try {
                const res = await fetch('/buka-token', { method: 'POST' });
                const data = await res.json();
                addLog(`Response: ${JSON.stringify(data)}`);
                
                if (data.status === 'SUCCESS') {
                    tokenOpened = true;
                    updateStatus('statusToken', 'Token berhasil dibuka!', true);
                    step3Btn.disabled = false;
                    showResult('success', 'Token berhasil dibuka! Sekarang klik "BUKA STEP3"');
                    addLog('✅ Token berhasil dibuka');
                } else {
                    updateStatus('statusToken', 'Token gagal dibuka', false);
                    showResult('error', data.message);
                    addLog(`❌ Gagal: ${data.message}`, true);
                }
            } catch (err) {
                addLog(`❌ Error: ${err.message}`, true);
                updateStatus('statusToken', 'Error: ' + err.message, false);
                showResult('error', err.message);
            } finally {
                btn.disabled = false;
            }
        }
        
        async function bukaStep3() {
            if (!tokenOpened) {
                alert('Buka token dulu!');
                return;
            }
            
            const btn = document.getElementById('step3Btn');
            btn.disabled = true;
            updateStatus('statusStep3', 'Membuka step3...', false);
            addLog('🚀 Membuka step3...');
            
            try {
                const res = await fetch('/buka-step3', { method: 'POST' });
                const data = await res.json();
                addLog(`Response: ${JSON.stringify(data)}`);
                
                if (data.status === 'SUCCESS') {
                    updateStatus('statusStep3', 'Step3 berhasil dibuka!', true);
                    showResult('success', 'Step3 berhasil dibuka!');
                    addLog('✅ Step3 berhasil dibuka');
                    
                    // Tampilkan iframe dengan step3
                    const step3Url = 'https://pom.bpjsketenagakerjaan.go.id/pu/step3';
                    document.getElementById('step3Frame').src = step3Url;
                    document.getElementById('step3Url').innerHTML = `🔗 ${step3Url}`;
                    document.getElementById('iframeContainer').style.display = 'block';
                } else {
                    updateStatus('statusStep3', 'Step3 gagal dibuka', false);
                    showResult('error', data.message);
                    addLog(`❌ Gagal: ${data.message}`, true);
                }
            } catch (err) {
                addLog(`❌ Error: ${err.message}`, true);
                updateStatus('statusStep3', 'Error: ' + err.message, false);
                showResult('error', err.message);
            } finally {
                btn.disabled = false;
            }
        }
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/buka-token', methods=['POST'])
def buka_token():
    result = bot.buka_token()
    return jsonify(result)


@app.route('/buka-step3', methods=['POST'])
def buka_step3():
    result = bot.buka_step3()
    return jsonify(result)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("="*50)
    print("POM BPJS Opener")
    print(f"Buka: http://localhost:{port}")
    print("="*50)
    app.run(debug=False, host='0.0.0.0', port=port)
