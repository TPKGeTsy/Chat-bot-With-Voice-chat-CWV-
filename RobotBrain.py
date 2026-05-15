import os
import time
import re
import whisper
import speech_recognition as sr
import ollama
import torch
import serial
import win32com.client 

# ==========================================
# CONFIGURATION (ตั้งค่าระบบ)
# ==========================================
USE_MIC = False        # สลับเป็น True เมื่อต้องการใช้ไมโครโฟน
WHISPER_MODEL = "base" # ใช้ "base" (เร็ว) หรือ "small" (แม่นยำ)
# ser = serial.Serial('COM3', 9600, timeout=1) # ปลดคอมเมนต์เมื่อเสียบสายบอร์ดจริง

# ==========================================
# 1. HARDWARE & TTS SYSTEM (ระบบเสียง SAPI5)
# ==========================================
# เชื่อมต่อกับระบบเสียง Windows โดยตรง (แก้ปัญหาไฟล์พัง)
speaker = win32com.client.Dispatch("SAPI.SpVoice")

def setup_voice():
    voices = speaker.GetVoices()
    for voice in voices:
        desc = voice.GetDescription()
        if "Thai" in desc or "Pattara" in desc:
            speaker.Voice = voice
            print(f"✅ เชื่อมต่อเสียงสำเร็จ: {desc}")
            return True
    print("⚠️ ไม่พบเสียงภาษาไทยในระบบ!")
    return False

HAS_THAI_VOICE = setup_voice()
speaker.Rate = 2 # ปรับความเร็วเสียงพูด

def clean_text(text):
    """ล้างอักขระพิเศษและอีโมจิออก ป้องกันหุ่นยนต์อ่านเพี้ยน"""
    if not text: return ""
    cleaned = re.sub(r'[^\u0e00-\u0e7fa-zA-Z0-9\s.,!?]', '', text)
    return cleaned.strip()

def speak(text):
    """ฟังก์ชันให้หุ่นยนต์พูด"""
    if not text: return
    cleaned_text = clean_text(text)
    if not cleaned_text: return
    
    print(f"🤖 Robot: {cleaned_text}")
    try:
        speaker.Speak(cleaned_text)
    except Exception as e:
        print(f"❌ ระบบเสียงขัดข้อง: {e}")

def move_robot(direction, value=None, unit=""):
    """จำลองการส่งคำสั่งไปที่ Hardware แบบมี Parameter"""
    if value is not None:
        cmd_str = f"{direction}_{value}" # เช่น FORWARD_SPEED_50
        print(f"\n[⚙️ HARDWARE ACTION]: ส่งสัญญาณ Serial -> {cmd_str} ({unit})")
    else:
        cmd_str = direction
        print(f"\n[⚙️ HARDWARE ACTION]: ส่งสัญญาณ Serial -> {cmd_str}")
        
    # เวลาต่อสาย Serial เข้าบอร์ดจริงๆ ค่อยปลดคอมเมนต์บรรทัดนี้
    # ser.write(f"{cmd_str}\n".encode()) 
    return True

# ==========================================
# 2. AI MODELS LOADING (โหลดหูฟัง Whisper)
# ==========================================
print(f"🚀 กำลังปลุกหูฟัง AI ({WHISPER_MODEL})")
stt_model = whisper.load_model(WHISPER_MODEL, device="cuda") 

# ==========================================
# 3. CORE LOGIC & MEMORY (ระบบสมองและการจำ)
# ==========================================
# สมุดจดความจำของ AI (เก็บ System Prompt ไว้บรรทัดแรกเสมอ)
chat_history = [
    {'role': 'system', 'content': 'นายคือ "แอร์เย็น" มีเจ้านายชื่อ "เกมเมอร์" หุ่นยนต์ผู้ช่วยอัจฉริยะ ตอบสั้นๆ ไม่เกิน 20 คำ ห้ามใส่อีโมจิ และสามารถจำบริบทการสนทนาก่อนหน้าได้'}
]

def handle_command(text):
    global chat_history 
    t = text.strip()
    if not t: return None
    
    # 🔍 ฟังก์ชันช่วยดึงตัวเลขออกจากประโยค
    def extract_number(t_str):
        numbers = re.findall(r'\d+', t_str)
        return int(numbers[0]) if numbers else None

    val = extract_number(t)
    
    # --- 1. คำสั่งควบคุมฮาร์ดแวร์ (พร้อมจับตัวเลข) ---
    if any(k in t for k in ["เดินหน้า", "ไปหน้า", "เคลื่อนที่"]):
        if val is not None:
            if "ความเร็ว" in t:
                move_robot("FORWARD_SPEED", val, "ความเร็ว")
                return f"รับทราบครับ กำลังเดินหน้าด้วยความเร็ว {val}"
            elif any(u in t for u in ["เมตร", "เซน", "ก้าว"]):
                move_robot("FORWARD_DIST", val, "ระยะทาง")
                return f"รับทราบครับ กำลังเคลื่อนที่ไปข้างหน้า {val} หน่วย"
        
        move_robot("FORWARD")
        return "รับทราบ กำลังเคลื่อนที่ไปข้างหน้าครับ"
        
    elif any(k in t for k in ["ถอยหลัง", "ถอย"]):
        if val is not None:
            if "ความเร็ว" in t:
                move_robot("BACKWARD_SPEED", val, "ความเร็ว")
                return f"รับทราบครับ กำลังถอยหลังด้วยความเร็ว {val}"
            elif any(u in t for u in ["เมตร", "เซน", "ก้าว"]):
                move_robot("BACKWARD_DIST", val, "ระยะทาง")
                return f"รับทราบครับ กำลังถอยหลังเป็นระยะ {val} หน่วย"
                
        move_robot("BACKWARD")
        return "รับทราบ กำลังถอยหลังครับ"
        
    elif any(k in t for k in ["หยุด", "จอด", "เลิกทำ"]):
        move_robot("STOP")
        return "หยุดการทำงานเรียบร้อยแล้วครับ"
        
    # --- 2. ส่งให้สมอง AI คิด (โหมดสนทนา) ---
    else:
        try:
            # จดสิ่งที่คุณพูด
            chat_history.append({'role': 'user', 'content': t})
            
            # ป้องกันหน่วยความจำล้น (เก็บแค่ 10 ประโยคล่าสุด)
            if len(chat_history) > 11:
                chat_history = [chat_history[0]] + chat_history[-10:]
            
            # ส่งประวัติทั้งหมดให้ Gemma 2 คิด
            response = ollama.chat(model='gemma2', messages=chat_history)
            bot_reply = response['message']['content']
            
            # จดสิ่งที่ AI ตอบ
            chat_history.append({'role': 'assistant', 'content': bot_reply})
            return bot_reply
        except Exception as e:
            print(f"🚨 Ollama Error: {e}")
            return "ขออภัยครับ สมองส่วนคิดขัดข้อง"

# ==========================================
# 4. INPUT SYSTEM (ระบบรับเสียง/คีย์บอร์ด)
# ==========================================
def get_user_input():
    if USE_MIC:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("\n[👂 กำลังฟัง...]")
            r.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = r.listen(source, phrase_time_limit=5)
                temp_input = "input_temp.wav"
                with open(temp_input, "wb") as f:
                    f.write(audio.get_wav_data())
                
                result = stt_model.transcribe(
                    temp_input, 
                    language="th",
                    initial_prompt="เดินหน้า 50 ถอยหลัง หยุด สวัสดี",
                    fp16=torch.cuda.is_available()
                )
                
                if os.path.exists(temp_input):
                    os.remove(temp_input)
                
                text = result["text"].strip()
                if text: print(f"👤 คุณพูดว่า: {text}")
                return text
            except:
                return None
    else:
        return input("\n[⌨️ พิมพ์คำสั่ง]: ")

# ==========================================
# 5. MAIN EXECUTION (ลูปหลักการทำงาน)
# ==========================================
if __name__ == "__main__":
    mode_text = "ไมโครโฟน" if USE_MIC else "คีย์บอร์ด"
    print(f"\n--- เริ่มระบบ RobotBrain (โหมด {mode_text}) ---")
    speak("ระบบปฏิบัติการพร้อมทำงานแล้วครับ")
    
    while True:
        try:
            user_input = get_user_input()
            if user_input and len(user_input) > 1:
                bot_reply = handle_command(user_input)
                if bot_reply:
                    speak(bot_reply)
        except KeyboardInterrupt:
            print("\n")
            speak("ปิดระบบแล้วครับ ไว้เจอกันใหม่ครับ")
            break
        except Exception as e:
            print(f"🚨 Main Loop Error: {e}")
            time.sleep(1)