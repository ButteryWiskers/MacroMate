from flask import Flask, request, jsonify, render_template_string
import struct
import time
import os
import sys
import random
import math
import logging

# ---- Logging Setup ----
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("server.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("pihid")

app = Flask(__name__)

HID_KEYBOARD = '/dev/hidg0'
HID_MOUSE = '/dev/hidg1'

# EXTENDED KEYCODE MAP, covers all from get_common_keys
KEYCODES = {
    # Letters
    **{ch: code for ch, code in zip(
        'abcdefghijklmnopqrstuvwxyz', range(0x04, 0x1e)
    )},
    # Numbers row
    **{str(n): code for n, code in zip(range(0, 10), range(0x27, 0x1e, -1))},
    # Numpad
    **{'num' + str(i): 0x59 + i for i in range(10)},
    'multiply': 0x55, 'add': 0x57, 'separator': 0x85, 'subtract': 0x56, 'decimal': 0x63, 'divide': 0x54,
    # Navigation
    'enter': 0x28, 'esc': 0x29, 'tab': 0x2b, 'backspace': 0x2a, 'delete': 0x4c, 'insert': 0x49, 'space': 0x2c,
    'shift': 0xe1, 'ctrl': 0xe0, 'ctrlleft': 0xe0, 'ctrlright': 0xe4, 'alt': 0xe2, 'altleft': 0xe2, 'altright': 0xe6,
    'win': 0xe3, 'winleft': 0xe3, 'winright': 0xe7, 'apps': 0x65,
    'up': 0x52, 'down': 0x51, 'left': 0x50, 'right': 0x4f,
    'home': 0x4a, 'end': 0x4d, 'pageup': 0x4b, 'pagedown': 0x4e,
    'capslock': 0x39, 'numlock': 0x53, 'scrolllock': 0x47, 'printscreen': 0x46, 'pause': 0x48,
    # F keys
    **{'f{}'.format(i): 0x3a + i - 1 for i in range(1, 13)},
}

# Mouse buttons
MOUSE_BUTTONS = {
    'left': 0x01, 'right': 0x02, 'middle': 0x04
}

def send_keyboard(report):
    with open(HID_KEYBOARD, 'wb') as f:
        f.write(report)
    logger.info(f"Sent keyboard report: {list(report)}")

def send_mouse(report):
    with open(HID_MOUSE, 'wb') as f:
        f.write(report)
    logger.info(f"Sent mouse report: {list(report)}")

def press_key(key, modifiers=0):
    keycode = KEYCODES.get(key.lower(), 0)
    report = struct.pack('BBBBBBBB', modifiers, 0, keycode, 0, 0, 0, 0, 0)
    send_keyboard(report)
    report = struct.pack('BBBBBBBB', 0, 0, 0, 0, 0, 0, 0, 0)
    send_keyboard(report)
    logger.info(f"Pressed key: {key} (modifiers={modifiers})")

def press_combo(keys):
    modifiers = 0
    keycodes = []
    for k in keys:
        code = KEYCODES.get(k.lower())
        if code is None:
            continue
        if code >= 0xe0:  # Modifier
            modifiers |= 1 << (code - 0xe0)
        else:
            keycodes.append(code)
    report = struct.pack('BB6B', modifiers, 0, *(keycodes + [0]* (6 - len(keycodes))))
    send_keyboard(report)
    report = struct.pack('BB6B', 0, 0, 0, 0, 0, 0, 0, 0)
    send_keyboard(report)
    logger.info(f"Pressed combo: {keys}")

def type_text(text):
    for char in text:
        k = char.lower()
        shift = 0
        if k.isalpha():
            if char.isupper():
                shift = 0x02  # Left Shift
            press_key(k, modifiers=shift)
        elif k == ' ':
            press_key('space')
        elif k in KEYCODES:
            press_key(k)
        else:
            pass
        time.sleep(0.05)
    logger.info(f"Typed text: {text}")

def send_relative_move(dx, dy, buttons=0, wheel=0, total_duration=0):
    moves = []
    dx_total, dy_total = dx, dy
    while dx != 0 or dy != 0:
        move_x = max(-128, min(127, dx))
        move_y = max(-128, min(127, dy))
        moves.append( (move_x, move_y) )
        dx -= move_x
        dy -= move_y

    steps = len(moves)
    sleep_time = total_duration / steps if steps > 0 and total_duration > 0 else 0.002

    for move_x, move_y in moves:
        report = struct.pack('bbbb', buttons, move_x, move_y, wheel)
        send_mouse(report)
        time.sleep(sleep_time)
    report = struct.pack('bbbb', 0, 0, 0, 0)
    send_mouse(report)
    logger.info(f"Relative move dx={dx_total}, dy={dy_total}, buttons={buttons}, wheel={wheel}, duration={total_duration}")

def get_current_mouse_pos():
    try:
        import pyautogui
        pos = pyautogui.position()
        return (pos.x, pos.y)
    except Exception:
        return (0, 0)

def bezier_interp(p0, p1, p2, t):
    return (
        int((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]),
        int((1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1])
    )

def humanized_smooth_move_abs(to_x, to_y, duration=0.3, steps=None, jitter=2):
    from_x, from_y = get_current_mouse_pos()
    if steps is None:
        distance = math.hypot(to_x - from_x, to_y - from_y)
        steps = max(10, int(distance // 4))
    ctrl_x = (from_x + to_x) / 2 + random.randint(-30, 30)
    ctrl_y = (from_y + to_y) / 2 + random.randint(-30, 30)
    last_x, last_y = from_x, from_y

    for i in range(1, steps + 1):
        t = i / steps
        x, y = bezier_interp((from_x, from_y), (ctrl_x, ctrl_y), (to_x, to_y), t)
        if i < steps:
            x += random.randint(-jitter, jitter)
            y += random.randint(-jitter, jitter)
        dx, dy = x - last_x, y - last_y
        if dx or dy:
            send_relative_move(dx, dy, total_duration=0)
        last_x, last_y = x, y
        sleep = duration * (0.5 + 0.5 * math.sin(math.pi * t)) / steps
        time.sleep(sleep)
    final_dx, final_dy = to_x - last_x, to_y - last_y
    if final_dx or final_dy:
        send_relative_move(final_dx, final_dy, total_duration=0)
    logger.info(f"Humanized smooth move to ({to_x},{to_y}) in {steps} steps with jitter={jitter}")

def smooth_move_offset(dx, dy, duration=0.3, steps=20):
    from_x, from_y = get_current_mouse_pos()
    to_x = from_x + dx
    to_y = from_y + dy
    humanized_smooth_move_abs(to_x, to_y, duration, steps)

# --- Webpage with reload and log ---
RELOAD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Pi HID Server Reload</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; background: #191d23; color: #eee; text-align: center; padding-top: 70px;}
        button { background: #28d; color: #fff; border: none; font-size: 1.4em; padding: 18px 40px; border-radius: 8px; cursor: pointer;}
        button:hover { background: #059; }
        #status { margin-top: 35px; color: #00fc5c; font-weight: bold;}
        #log { max-width:800px; margin:20px auto; background:#222; color:#fff; text-align:left; padding:8px 12px; border-radius:6px; min-height:120px; font-family:monospace; font-size:1em; overflow:auto;}
    </style>
</head>
<body>
    <h2>Reload Pi HID Server</h2>
    <form id="reloadForm">
        <button type="submit">Reload Server</button>
    </form>
    <div id="status"></div>
    <hr>
    <h3>Server Log (last 100 lines)</h3>
    <div id="log"></div>
    <button onclick="reloadLog(); return false;">Refresh Log</button>
    <script>
    function reloadLog() {
        fetch('/log').then(r => r.text()).then(txt => {
            document.getElementById('log').innerHTML = txt;
        });
    }
    window.onload = reloadLog;
    document.getElementById('reloadForm').onsubmit = async function(e) {
        e.preventDefault();
        document.getElementById('status').innerText = 'Reloading server...';
        try {
            let resp = await fetch('/reload', {method: 'POST'});
            if (resp.ok) {
                document.getElementById('status').innerText = 'Server reloading! Please refresh after a few seconds.';
            } else {
                document.getElementById('status').innerText = 'Reload failed: ' + resp.statusText;
            }
        } catch (err) {
            document.getElementById('status').innerText = 'Error: ' + err;
        }
    };
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(RELOAD_HTML)

@app.route('/log')
def log():
    log_path = "server.log"
    try:
        with open(log_path, "r") as f:
            lines = f.readlines()
        return "<pre>" + "".join(lines[-100:]) + "</pre>"
    except Exception as e:
        return f"<pre>Error reading log: {e}</pre>"

@app.route('/action', methods=['POST'])
def handle_action():
    data = request.json
    typ = data.get('type')
    logger.info(f"Received action: {typ} | Data: {data}")
    if typ == 'key':
        action = data.get('action', 'press')
        key = data.get('key')
        if isinstance(key, list):
            press_combo(key)
            return jsonify({'status': 'ok'})
        if action == 'press':
            press_key(key)
        elif action == 'down':
            keycode = KEYCODES.get(key.lower(), 0)
            if keycode >= 0xe0:
                modifiers = 1 << (keycode - 0xe0)
                report = struct.pack('BBBBBBBB', modifiers, 0, 0, 0, 0, 0, 0, 0)
            else:
                report = struct.pack('BBBBBBBB', 0, 0, keycode, 0, 0, 0, 0, 0)
            send_keyboard(report)
        elif action == 'up':
            report = struct.pack('BBBBBBBB', 0, 0, 0, 0, 0, 0, 0, 0)
            send_keyboard(report)
        return jsonify({'status': 'ok'})
    elif typ == 'type':
        text = data.get('text', '')
        type_text(text)
        return jsonify({'status': 'ok'})
    elif typ == 'click':
        button = data.get('button', 'left_click')
        btn_bits = 0
        if button.startswith('left'):
            btn_bits |= MOUSE_BUTTONS['left']
        if button.startswith('right'):
            btn_bits |= MOUSE_BUTTONS['right']
        if button.startswith('middle'):
            btn_bits |= MOUSE_BUTTONS['middle']
        report = struct.pack('BBBB', btn_bits, 0, 0, 0)
        send_mouse(report)
        report = struct.pack('BBBB', 0, 0, 0, 0)
        send_mouse(report)
        return jsonify({'status': 'ok'})
    elif typ == 'mouse_move':
        x = int(data.get('x', 0))
        y = int(data.get('y', 0))
        buttons = int(data.get('buttons', 0)) if 'buttons' in data else 0
        wheel = int(data.get('wheel', 0)) if 'wheel' in data else 0
        duration = float(data.get('duration', 0))
        send_relative_move(x, y, buttons, wheel, duration)
        return jsonify({'status': 'ok'})
    elif typ == 'smooth_move':
        to_x = int(data.get('to_x'))
        to_y = int(data.get('to_y'))
        duration = float(data.get('duration', 0.3))
        jitter = int(data.get('jitter', 2))
        steps = data.get('steps')
        steps = int(steps) if steps is not None else None
        humanized_smooth_move_abs(to_x, to_y, duration, steps, jitter)
        return jsonify({'status': 'ok'})
    elif typ == 'smooth_move_offset':
        dx = int(data.get('dx'))
        dy = int(data.get('dy'))
        duration = float(data.get('duration', 0.3))
        steps = int(data.get('steps', 20))
        smooth_move_offset(dx, dy, duration, steps)
        return jsonify({'status': 'ok'})
    else:
        logger.warning(f"Unknown action type: {typ}")
        return jsonify({'error': 'unknown action'}), 400

@app.route('/ping')
def ping():
    return 'pong'

@app.route('/reload', methods=['POST', 'GET'])
def reload_server():
    if request.method == 'POST':
        logger.info("Reload requested via /reload endpoint!")
        sys.stdout.flush()
        os.execv(sys.executable, [sys.executable] + sys.argv)
        return jsonify({'status': 'restarting'})
    else:
        return "<h3>Reload endpoint. Please use the main page to reload.</h3>"

if __name__ == '__main__':
    logger.info("Starting Pi HID Flask Server on 0.0.0.0:8080")
    app.run(host='0.0.0.0', port=8080)
