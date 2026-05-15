import streamlit as st
import time
import re
import whisper
import ollama
import torch
import win32com.client
import os
from audio_recorder_streamlit import audio_recorder

# ==========================================
# 1. INITIALIZE & CACHE MODELS
# ==========================================
@st.cache_resource
def load_whisper():
    return whisper.load_model("base", device="cuda" if torch.cuda.is_available() else "cpu")

@st.cache_resource
def get_speaker():
    # ใช้ Dispatch เพื่อคุยกับ SAPI5 ของ Windows
    speaker = win32com.client.Dispatch("SAPI.SpVoice")
    voices = speaker.GetVoices()
    for v in voices:
        if "Thai" in v.GetDescription() or "Pattara" in v.GetDescription():
            speaker.Voice = v
            break
    speaker.Rate = 2 
    return speaker

st_model = load_whisper()
speaker = get_speaker()

# ==========================================
# 2. SESSION STATE
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "คุณคือ 'แอร์เย็น' หุ่นยนต์พ่อบ้านอัจฉริยะ เป็นมืออาชีพ ตอบสั้นๆ ไม่เกิน 20 คำ ห้ามใส่อีโมจิเด็ดขาด"}
    ]

if "last_audio" not in st.session_state:
    st.session_state.last_audio = None

# ==========================================
# 3. FUNCTIONS
# ==========================================
def speak_offline(text):
    """พูดแบบ Sync เพื่อรอให้จบประโยคก่อนคืนค่า"""
    cleaned = re.sub(r'[^\u0e00-\u0e7fa-zA-Z0-9\s.,!?]', '', text)
    if cleaned:
        try:
            # การ Speak แบบปกติจะบล็อก Process ไว้จนกว่าจะพูดจบ
            # ทำให้ Streamlit ไม่รีบรัน st.rerun() จนเสียงตัด
            speaker.Speak(cleaned)
            time.sleep(0.3) # Buffer เล็กน้อยให้ระบบเสียงคืนค่า
        except Exception as e:
            print(f"Speech Error: {e}")

def move_robot(direction):
    st.toast(f"⚙️ ส่งสัญญาณฮาร์ดแวร์: {direction}") 
    print(f"[SERIAL OUT] -> {direction}")

def process_command(text_input):
    """ฟังก์ชันคิดและบันทึกคำตอบ"""
    st.session_state.messages.append({"role": "user", "content": text_input})
    
    # Logic ควบคุม
    if any(k in text_input for k in ["เดินหน้า", "ไปหน้า"]):
        move_robot("FORWARD")
        bot_reply = "รับทราบ กำลังเดินหน้าครับ"
    elif any(k in text_input for k in ["ถอยหลัง", "ถอย"]):
        move_robot("BACKWARD")
        bot_reply = "รับทราบ กำลังถอยหลังครับ"
    elif any(k in text_input for k in ["หยุด", "จอด"]):
        move_robot("STOP")
        bot_reply = "หยุดระบบขับเคลื่อนแล้วครับ"
    else:
        try:
            res = ollama.chat(model='gemma2', messages=st.session_state.messages)
            bot_reply = res['message']['content']
        except Exception as e:
            bot_reply = "สมองส่วนคิดขัดข้องครับ"
            
    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
    
    # แสดงผลบน UI ก่อนพูด
    speak_offline(bot_reply)
    st.rerun()

# ==========================================
# 4. UI LAYOUT
# ==========================================
st.set_page_config(page_title="Air Yen OS", page_icon="🤖", layout="wide")

st.title("🤖 Air Yen - Robot Control Center")
st.markdown("---")

col_chat, col_ctrl = st.columns([7, 3])

with col_chat:
    st.subheader("💬 Chat with Air Yen")
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if prompt := st.chat_input("พิมพ์คำสั่งให้แอร์เย็นที่นี่..."):
        process_command(prompt)

with col_ctrl:
    st.subheader("🕹️ Manual Control")
    col_u1, col_u2, col_u3 = st.columns(3)
    with col_u2:
        if st.button("⬆️ เดินหน้า", use_container_width=True):
            move_robot("FORWARD"); speak_offline("เดินหน้าครับ")
    
    col_l, col_s, col_r = st.columns(3)
    with col_l:
        if st.button("⬅️ ซ้าย", use_container_width=True):
            move_robot("LEFT"); speak_offline("เลี้ยวซ้ายครับ")
    with col_s:
        if st.button("🛑 หยุด", use_container_width=True, type="primary"):
            move_robot("STOP"); speak_offline("หยุดครับ")
    with col_r:
        if st.button("➡️ ขวา", use_container_width=True):
            move_robot("RIGHT"); speak_offline("เลี้ยวขวาครับ")
            
    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b2:
        if st.button("⬇️ ถอยหลัง", use_container_width=True):
            move_robot("BACKWARD"); speak_offline("ถอยหลังครับ")

    st.markdown("---")
    st.subheader("🎙️ Voice Command")
    
    # 🚨 GUARD: หุ้มด้วย Try-Except และเช็คค่า None เพื่อกัน Error แดงตอนเปิดแอป
    try:
        audio_bytes = audio_recorder(
            text="🎤 จิ้มเพื่อพูด", 
            recording_color="#e8b12f", 
            neutral_color="#6aa36f",
            icon_size="2x"
        )
    except Exception:
        audio_bytes = None

    # ตรวจสอบว่ามีข้อมูลเสียงใหม่และไม่ซ้ำเดิม
    if audio_bytes is not None and audio_bytes != st.session_state.last_audio:
        st.session_state.last_audio = audio_bytes
        
        with st.spinner("แอร์เย็นกำลังฟัง..."):
            temp_file = "voice_temp.wav"
            with open(temp_file, "wb") as f:
                f.write(audio_bytes)
            
            # Whisper ประมวลผล
            result = st_model.transcribe(
                temp_file, 
                language="th", 
                fp16=torch.cuda.is_available(),
                condition_on_previous_text=False,
                no_speech_threshold=0.6
            )
            voice_text = result["text"].strip()
            
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
            if "<|" in voice_text or len(voice_text) < 2:
                voice_text = ""
                
        if voice_text:
            st.toast(f"👂 ได้ยินว่า: {voice_text}")
            process_command(voice_text)