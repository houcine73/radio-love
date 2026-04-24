from flask import Flask, request, send_file, jsonify
import os
import uuid
import wave
import struct
import math
from gtts import gTTS
import logging

app = Flask(__name__)
UPLOAD_FOLDER = "audio"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# إعداد تسجيل الأخطاء
logging.basicConfig(level=logging.INFO)

# دالة احتياطية لتوليد نغمة (في حال فشل gTTS)
def generate_tone_wav(filename, frequency=440, duration=2, sample_rate=44100, amplitude=16000):
    num_samples = int(sample_rate * duration)
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for i in range(num_samples):
            value = int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate))
            data = struct.pack('<h', value)
            wav_file.writeframes(data)

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>راديو الحب القديم - متعدد اللغات</title>
        <style>
            body {
                background: #2b1a1a;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                text-align: center;
                padding: 50px;
                color: #f0e6d0;
            }
            .radio-box {
                background: #3d2a2a;
                padding: 30px;
                border-radius: 20px;
                max-width: 550px;
                margin: auto;
                box-shadow: 0 0 20px rgba(0,0,0,0.5);
                border: 1px solid #b8860b;
            }
            textarea {
                width: 90%;
                height: 120px;
                margin: 20px 0;
                padding: 10px;
                font-size: 16px;
                background: #fef7e0;
                border: 1px solid #b8860b;
                border-radius: 10px;
                font-family: inherit;
            }
            select, button {
                background: #b8860b;
                color: white;
                border: none;
                padding: 12px 25px;
                font-size: 16px;
                margin: 10px;
                cursor: pointer;
                border-radius: 40px;
                transition: 0.2s;
            }
            select {
                background: #5a3a2a;
            }
            button:hover, select:hover {
                background: #d4a017;
                transform: scale(1.02);
            }
            .onair {
                color: #ff5555;
                font-size: 14px;
                letter-spacing: 2px;
                margin-bottom: 10px;
            }
            audio {
                margin-top: 20px;
                width: 100%;
            }
            #status {
                margin-top: 15px;
                font-style: italic;
            }
            .send-btn {
                background: #8b0000;
                margin-top: 20px;
            }
            .send-btn:hover {
                background: #a52a2a;
            }
        </style>
    </head>
    <body>
        <div class="radio-box">
            <div class="onair">🔴 ON AIR</div>
            <h1>📻 راديو الحب القديم</h1>
            <p>ليست كل الرسائل تحتاج أن تُكتب... بعضها يحتاج أن تصل</p>
            
            <select id="langSelect">
                <option value="ar">🇸🇦 العربية</option>
                <option value="es">🇪🇸 Español</option>
                <option value="pt">🇵🇹 Português</option>
                <option value="en">🇬🇧 English</option>
                <option value="fr">🇫🇷 Français</option>
            </select>
            
            <textarea id="msg" placeholder="اكتب رسالتك... / Escribe tu mensaje... / Escreva sua mensagem... / Write your message... / Écrivez votre message..."></textarea><br/>
            <button id="generateBtn">🎙️ أرسل رسالتك</button>
            <audio id="audio" controls style="display:none;"></audio>
            <div id="status"></div>
        </div>

        <script>
            const generateBtn = document.getElementById('generateBtn');
            const audioPlayer = document.getElementById('audio');
            const statusDiv = document.getElementById('status');
            let currentAudioUrl = null;
            let currentText = '';
            let currentLang = 'ar';

            generateBtn.onclick = async () => {
                const text = document.getElementById('msg').value.trim();
                const lang = document.getElementById('langSelect').value;
                if (!text) {
                    alert('الرجاء كتابة رسالة / Please write a message');
                    return;
                }
                currentText = text;
                currentLang = lang;
                statusDiv.innerText = '📡 جاري البث... / Transmitting...';
                generateBtn.disabled = true;

                try {
                    const response = await fetch('/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text: text, lang: lang })
                    });
                    if (!response.ok) {
                        const errorText = await response.text();
                        throw new Error(errorText);
                    }
                    const blob = await response.blob();
                    if (currentAudioUrl) URL.revokeObjectURL(currentAudioUrl);
                    currentAudioUrl = URL.createObjectURL(blob);
                    audioPlayer.src = currentAudioUrl;
                    audioPlayer.style.display = 'block';
                    audioPlayer.play();
                    statusDiv.innerText = '✅ تم البث. استمع لرسالتك. / Broadcast complete. Listen to your message.';

                    // إظهار زر الإرسال (المدفوع) بعد التشغيل
                    let existingSendBtn = document.getElementById('dynamicSendBtn');
                    if (!existingSendBtn) {
                        const sendBtn = document.createElement('button');
                        sendBtn.id = 'dynamicSendBtn';
                        sendBtn.innerText = '📩 اجعلها تصل (7$) / Send it (7$)';
                        sendBtn.className = 'send-btn';
                        sendBtn.onclick = () => {
                            window.location.href = '/checkout?text=' + encodeURIComponent(currentText) + '&lang=' + currentLang;
                        };
                        document.querySelector('.radio-box').appendChild(sendBtn);
                    }
                } catch (err) {
                    statusDiv.innerText = '❌ خطأ: ' + err.message;
                    console.error(err);
                } finally {
                    generateBtn.disabled = false;
                }
            };
        </script>
    </body>
    </html>
    '''

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    text = data.get('text', '')
    lang = data.get('lang', 'ar')  # اللغة المختارة من المستخدم
    if not text:
        return 'لا يوجد نص / No text', 400

    file_id = str(uuid.uuid4())
    mp3_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.mp3")
    wav_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.wav")

    # قائمة اللغات المدعومة من gTTS
    supported_langs = ['ar', 'es', 'pt', 'en', 'fr']
    if lang not in supported_langs:
        lang = 'en'  # افتراضي

    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(mp3_path)
        app.logger.info(f"Generated speech for text: {text[:30]}... in language {lang}")
        return send_file(mp3_path, mimetype='audio/mpeg')
    except Exception as e:
        app.logger.error(f"gTTS failed: {e}")
        # فشل gTTS: نستخدم النغمة الاحتياطية (wav)
        generate_tone_wav(wav_path, frequency=440, duration=2)
        return send_file(wav_path, mimetype='audio/wav')

@app.route('/checkout')
def checkout():
    text = request.args.get('text', '')
    lang = request.args.get('lang', 'ar')
    # ضع رابط منتجك الفعلي على Gumroad هنا
    gumroad_link = "https://juliolegacy.gumroad.com/l/radio-love"  # استبدله برابطك
    
    # تحديد نص الصفحة حسب اللغة (مبسط)
    if lang == 'ar':
        title = "إرسال رسالتك"
        msg_title = "رسالتك:"
        instruction = "بعد الدفع، سنرسل لك رابطاً خاصاً يمكنك مشاركته مع من تحب."
        button_text = "💳 ادفع 7$ وأرسل الرسالة"
        footer = "سيتم توجيهك إلى Gumroad للدفع الآمن."
    elif lang == 'es':
        title = "Enviar tu mensaje"
        msg_title = "Tu mensaje:"
        instruction = "Después del pago, te enviaremos un enlace especial para que lo compartas con quien quieras."
        button_text = "💳 Paga 7$ y envía el mensaje"
        footer = "Serás redirigido a Gumroad para un pago seguro."
    elif lang == 'pt':
        title = "Enviar sua mensagem"
        msg_title = "Sua mensagem:"
        instruction = "Após o pagamento, enviaremos um link especial para você compartilhar com quem desejar."
        button_text = "💳 Pague 7$ e envie a mensagem"
        footer = "Você será redirecionado ao Gumroad para pagamento seguro."
    elif lang == 'fr':
        title = "Envoyer votre message"
        msg_title = "Votre message :"
        instruction = "Après le paiement, nous vous enverrons un lien spécial à partager avec vos proches."
        button_text = "💳 Payez 7$ et envoyez le message"
        footer = "Vous serez redirigé vers Gumroad pour un paiement sécurisé."
    else:
        title = "Send your message"
        msg_title = "Your message:"
        instruction = "After payment, we will send you a special link to share with your loved one."
        button_text = "💳 Pay $7 and send the message"
        footer = "You will be redirected to Gumroad for secure payment."

    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>{title}</title>
    <style>
        body {{ background: #2b1a1a; color: #f0e6d0; text-align: center; padding: 50px; font-family: Arial; }}
        .box {{ background: #3d2a2a; padding: 30px; border-radius: 20px; max-width: 500px; margin: auto; }}
        a {{ background: #b8860b; color: white; padding: 12px 25px; text-decoration: none; border-radius: 40px; display: inline-block; margin-top: 20px; }}
    </style>
    </head>
    <body>
    <div class="box">
        <h1>📻 {title}</h1>
        <p><strong>{msg_title}</strong> "{text}"</p>
        <p>{instruction}</p>
        <a href="{gumroad_link}" target="_blank">{button_text}</a>
        <p style="margin-top: 20px; font-size: 0.8rem;">{footer}</p>
    </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
