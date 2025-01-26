from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import traceback
import sys
import logging
import pythoncom  # เพิ่ม import นี้ที่ด้านบนของไฟล์
import win32api
import win32con
import time
import os
from logging.handlers import RotatingFileHandler
import socket

# ตั้งค่า logging
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media_control.log')
handler = RotatingFileHandler(log_file, maxBytes=10000, backupCount=1)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# เพิ่ม error handling
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

app = Flask(__name__)
CORS(app)

def set_system_volume(volume_level):
    try:
        # เริ่มต้น COM interface
        pythoncom.CoInitialize()
        
        logger.debug(f"กำลังตั้งค่าระดับเสียง: {volume_level}")
        
        if sys.platform != 'win32':
            logger.debug("รองรับเฉพาะ Windows เท่านั้น")
            return False

        # เพิ่มการจัดการข้อผิดพลาดเมื่อไม่พบ audio device
        try:
            devices = AudioUtilities.GetSpeakers()
            if not devices:
                logger.debug("ไม่พบอุปกรณ์เสียง")
                return False
        except Exception as e:
            logger.debug(f"ไม่สามารถเข้าถึงอุปกรณ์เสียง: {e}")
            return False

        interface = devices.Activate(
            IAudioEndpointVolume._iid_, 
            CLSCTX_ALL, 
            None
        )
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        # แปลงค่าระดับเสียง
        volume_scalar = max(0, min(1, float(volume_level)))
        volume.SetMasterVolumeLevelScalar(volume_scalar, None)
        
        logger.debug(f"ตั้งค่าระดับเสียงสำเร็จ: {volume_scalar}")
        return True
    except Exception as e:
        # บันทึกข้อผิดพลาดโดยละเอียด
        logger.debug(f"เกิดข้อผิดพลาดในการตั้งค่าเสียง: {e}")
        traceback.print_exc()
        return False
    finally:
        # คืนทรัพยากร COM
        pythoncom.CoUninitialize()

# เพิ่มฟังก์ชันจำลองการกดแป้นพิมพ์
def simulate_key_press(key_code):
    """จำลองการกดปุ่มคีย์บอร์ด"""
    try:
        pythoncom.CoInitialize()
        # เพิ่มการหน่วงเวลาเล็กน้อยก่อนกดปุ่ม
        time.sleep(0.1)
        
        # กดปุ่มค้างไว้นานขึ้น
        win32api.keybd_event(key_code, 0, 0, 0)  # กดปุ่ม
        time.sleep(0.2)  # เพิ่มเวลาการกดปุ่ม
        win32api.keybd_event(key_code, 0, win32con.KEYEVENTF_KEYUP, 0)  # ปล่อยปุ่ม
        
        # เพิ่มการหน่วงเวลาหลังปล่อยปุ่ม
        time.sleep(0.1)
        return True
    except Exception as e:
        logger.debug(f"เกิดข้อผิดพลาดในการจำลองการกดปุ่ม: {e}")
        return False
    finally:
        pythoncom.CoUninitialize()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/set_volume', methods=['POST'])
def set_volume():
    try:
        data = request.json
        if not data or 'volume' not in data:
            return jsonify({"status": "error", "message": "ข้อมูลไม่ถูกต้อง"}), 400

        volume_level = float(data['volume'])
        if volume_level < 0 or volume_level > 1:
            return jsonify({"status": "error", "message": "ระดับเสียงต้องอยู่ระหว่าง 0 และ 1"}), 400

        success = set_system_volume(volume_level)
        if not success:
            return jsonify({"status": "error", "message": "ไม่สามารถตั้งค่าระดับเสียงได้"}), 500

        return jsonify({"status": "success", "volume": volume_level})
    except Exception as e:
        logger.debug(f"เกิดข้อผิดพลาดในการประมวลผล: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_volume', methods=['GET'])
def get_volume():
    try:
        pythoncom.CoInitialize()
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
            IAudioEndpointVolume._iid_, 
            CLSCTX_ALL, 
            None
        )
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        current_volume = volume.GetMasterVolumeLevelScalar()
        return jsonify({"status": "success", "volume": current_volume})
    except Exception as e:
        logger.debug(f"เกิดข้อผิดพลาดในการดึงระดับเสียง: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        pythoncom.CoUninitialize()

# เพิ่ม routes สำหรับควบคุมการเล่น
@app.route('/media_control', methods=['POST'])
def media_control():
    try:
        data = request.json
        if not data or 'action' not in data:
            return jsonify({"status": "error", "message": "ข้อมูลไม่ถูกต้อง"}), 400

        action = data['action']
        success = False

        if action == 'previous':
            # ลองกดปุ่มซ้ำสองครั้ง
            success = simulate_key_press(0xB1)  # VK_LEFT (ArrowLeft)
        elif action == 'play':
            success = simulate_key_press(0xB3)  # VK_MEDIA_PLAY_PAUSE
        elif action == 'next':
            success = simulate_key_press(0xB0)  # VK_RIGHT (ArrowRight)

        if success:
            return jsonify({"status": "success", "action": action})
        else:
            return jsonify({"status": "error", "message": "ไม่สามารถดำเนินการได้"}), 500

    except Exception as e:
        logger.debug(f"เกิดข้อผิดพลาดในการควบคุมมีเดีย: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def get_local_ip():
    try:
        # สร้าง socket เพื่อหา local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

if __name__ == '__main__':
    try:
        local_ip = get_local_ip()
        print(f"Server running at: http://{local_ip}:5000")
        logger.info(f"Server started on {local_ip}:5000")
        app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")