import json
from microdot import Microdot, Response, send_file #Microdot handles web service
from microdot.websocket import with_websocket #websocket Microdot extension
import uasyncio as asyncio #allows aynchronous task handling
import hotspot_control
import information
import network
import os
from pubsub import getPubSub, PubSub, Topics, Origin
from utils import Config, CONFIG_FILE

WEB_ROOT = "/static"
STREAM_THRESHOLD = 1024  # 1 KB

config = Config()
app = Microdot()

def load_status_template():
    """Load the status response template."""
    try:
        with open(WEB_ROOT + "/html/status_response.html", "r") as f:
            return f.read()
    except OSError:
        return None


@app.get('/')
async def index(request):
    return Response(status_code=302, headers={'Location': '/remote-page'})


temp_buf = None
def stream_file(path):
    global temp_buf
    if temp_buf == None:
        temp_buf = bytearray(STREAM_THRESHOLD)
    try:
        with open(path, 'rb') as f:
            while True:
                numBytes = f.readinto(temp_buf, STREAM_THRESHOLD)
                if not numBytes:
                    break
                yield temp_buf
    except OSError:
        # Not really sure what else to do here
        yield b'Error reading file'


def guess_mime_type(filename):
    if filename.endswith('.html'):
        return 'text/html'
    if filename.endswith('.css'):
        return 'text/css'
    if filename.endswith('.js'):
        return 'application/javascript'
    if filename.endswith('.json'):
        return 'application/json'
    if filename.endswith('.svg'):
        return 'image/svg+xml'
    if filename.endswith('.png'):
        return 'image/png'
    if filename.endswith('.jpg') or filename.endswith('.jpeg'):
        return 'image/jpeg'
    if filename.endswith('.gif'):
        return 'image/gif'
    return 'application/octet-stream'


def is_file(path):
    try:
        return (os.stat(path)[0] & 0o170000) == 0o100000  # regular file
    except OSError:
        return False
    

def get_size(path):
    try:
        return os.stat(path)[6]
    except OSError:
        return 0


def serve_static_file(request, path):
    if '..' in path:
        # directory traversal is not allowed
        return "Bad Request", 400

    base_path = WEB_ROOT + '/' + path
    gz_path = base_path + '.gz'

    # Prefer .gz version if it exists
    try:
        if is_file(gz_path):
            
            if get_size(gz_path) > STREAM_THRESHOLD:
                mime = guess_mime_type(base_path)
                return Response(
                    stream_file(gz_path), 
                    headers = {
                        'Content-Type': mime, 
                        'Content-Encoding': "gzip"
                    }
                )
            return send_file(gz_path, compressed=True, max_age=1)
        
        # Fallback to uncompressed version
        if get_size(base_path):
            if get_size(base_path) > STREAM_THRESHOLD:
                mime = guess_mime_type(base_path)
                return Response(
                    stream_file(base_path), 
                    headers = {'Content-Type': mime}
                )
            return send_file(base_path, max_age=1)
    except Exception as e:
        print("unexpected error in serve_web_file", e)

    return 'Not found', 404


@app.route(WEB_ROOT + '/<path:path>')
def web_root(request, path):
    return serve_static_file(request, path)


@app.route('/generate_204')
async def generate_204(request):
    return Response('', status_code=302, headers={'Location': 'http://10.0.0.1/'})


@app.route('/ncsi.txt')
async def ncsi_txt(request):
    return Response('No Connectivity', headers={'Content-Type': 'text/plain'})


@app.route('/hotspot-detect.html')
async def hotspot_detect(request):
    return Response("<html><body>Redirecting</body></html>", status_code=302, headers={'Location': '/control-panel'})


@app.route('/library/test/success.html')
async def apple_success(request):
    return Response('', status_code=302, headers={'Location': 'http://10.0.0.1/'})

# WebSocket endpoint with added debug prints for remote commands

pubsub_remote_origin = None
remote_websockets = None
async def _on_message_remote(payload: str, topic: str, origin: Origin):
    # Send to WebSocket clients:
    global remote_websockets
    for ws in remote_websockets:
        message = origin.name + ":" + payload
        try:
            await ws.send(message)
            print(f"tx: {origin.name}: [{message.strip()}]. rx: {pubsub_remote_origin.name}")
        except Exception as e:
            print("Error broadcasting to remote client:", e)

@app.route('/ws')
@with_websocket
async def ws_endpoint(request, ws):
    print("WebSocket connection established")
    global remote_websockets
    remote_websockets.add(ws)

    try:
        while True:
            msg = await ws.receive()
            if msg is None:
                print("WebSocket connection closed by client")
                break
            elif msg == "pwr":
                full_command = "pwr on\r\n"
            else:
                full_command = "remote " + msg + "\r\n"

            getPubSub().publish(Topics.REMOTE_MESSAGE, full_command, pubsub_remote_origin)
    finally:
        remote_websockets.remove(ws)
        print("WebSocket client removed")

@app.get('/remote-page')
def remote_page(request):
    # not prefexing with WEB_ROOT is intentional to satisfy requirements of serve_web_file
    return serve_static_file(request, 'html/remote.html')

@app.get('/terminal')
def terminal_page(request):
    # not prefexing with WEB_ROOT is intentional to satisfy requirements of serve_web_file
    return serve_static_file(request, 'html/terminal.html')

@app.get('/control-panel')
def control_panel(request):
    # not prefexing with WEB_ROOT is intentional to satisfy requirements of serve_web_file
    return serve_static_file(request, 'html/control_panel.html')

# Terminal WebSocket endpoint for serial commands (no "remote" prefix)

pubsub_terminal_origin = None
terminal_websockets = None

async def _on_message_terminal(payload: any, topic: str, origin: Origin):
    # Send to WebSocket clients:
    global terminal_websockets
    for ws in terminal_websockets:
        message = f"[{origin.name}] {topic} > {str(payload)}"
        try:
            await ws.send(message)
            print(f"tx: {origin.name}: [{message.strip()}]. rx: {pubsub_terminal_origin.name}")
        except Exception as e:
            print("Error broadcasting to terminal client:", e)


@app.route('/ws_terminal')
@with_websocket
async def ws_terminal(request, ws):
    print("Terminal WebSocket connection established")
    global terminal_websockets
    terminal_websockets.add(ws)
    try:
        while True:
            msg = await ws.receive()
            print("Terminal WebSocket received:", msg)
            if msg is None:
                print("Terminal WebSocket connection closed by client")
                break
            # Terminal javascript code appends "\r\n" to the message, so no need to add it here
            print("Broadcasting terminal command:", msg)
            getPubSub().publish(Topics.TERMINAL_MESSAGE, msg, pubsub_terminal_origin)
            
    finally:
        terminal_websockets.remove(ws)
        print("Terminal WebSocket client removed")

@app.route('/control-panel-data')
async def control_panel_data(request):
    wifi_info = await information.get_wifi_info()
    hotspot_mode_value = hotspot_control.get_hotspot_mode()

    try:
        data = config.get_config()
        saved_connection_exists = True
        saved_ssid = data["wirelessClient"]["ssid"]
    except KeyError:
        saved_connection_exists = False
        saved_ssid = None

    ssid_info = { 
        "hotspot_ssid": wifi_info.get('ssid', 'unknown'),
        "domain": "tinklink.local",
        "ip": wifi_info.get('ip', '0.0.0.0'),
        "hotspot_mode": hotspot_mode_value,
        "saved_ssid": saved_ssid if saved_connection_exists and saved_ssid else "None"
    }
    
    connected = wifi_info.get('sta_connected', False)
    sta = {
         "sta_status": "Connected" if connected else "Not Connected",
         "sta_ssid": wifi_info.get('sta_ssid', 'N/A') or "N/A",
         "sta_ip": wifi_info.get('sta_ip', '0.0.0.0')
    }
    
    control_panel_data = {
        "connected": connected,
        "ssid_info": ssid_info, 
        "sta": sta, 
        "saved_connection_exists": saved_connection_exists
    }

    return json.dumps(control_panel_data), 200, { "Content-Type": "application/json"}

@app.get('/get-config')
async def get_json_config(request):
    return config.get_config()

@app.post('/save-config')
async def save_config(request):

    data = config.get_config()
    payload = request.json

    key = payload["formName"]
    try:
        if key == "triggers":
            data["switchers"][0][key] = payload[key]
        elif key == "switcher":
            data["switchers"][0]["connection"] = payload[key]["connection"]
            data["switchers"][0]["enabled"] = payload[key]["enabled"]
            data["switchers"][0]["type"] = payload[key]["type"]
            data["switchers"][0]["name"] = payload[key]["name"]
            data["switchers"][0]["connection_type"] = payload[key]["connection_type"]
        else:
            data[key] = payload[key]

        config.write_config(data)

        print(f"Updated configuration with {payload}")
    except Exception as e:
        print(f"Could not update configuration: {e}, payload is {payload}")
        return { 'Error': f'Could not update configuration {e}' }

    return { 'ok': 'Configuration Saved' }

@app.get('/scan_networks')
async def get_networks(request):
    found_ssids = await information.do_wifi_scan()
    information.update_scanned_networks(found_ssids)
    return json.dumps(found_ssids), 200, {'Content-Type': 'application/json' }

# Set hotspot mode status response
@app.post('/set_hotspot_mode')
async def set_hotspot_mode(request):
    mode = request.form.get('mode')
    if mode not in ["5-minute_time_out", "always_on"]:
        return Response("Invalid mode", status_code=400)
    display_mode = "5-Minute Time-Out" if mode == "5-minute_time_out" else "Always On"
    try:
        with open("hotspot_mode.txt", "w") as f:
            f.write(display_mode)
    except Exception as e:
        return Response("Failed to set hotspot mode: " + str(e), status_code=500)
    if display_mode == "5-Minute Time-Out":
        hotspot_control.start_countdown()
    else:
        hotspot_control.cancel_countdown()
    template = load_status_template()
    if template is None:
        return Response("Template not found", status_code=500)
    html = template.replace("{{MESSAGE}}", "Hotspot Mode Set To " + display_mode)
    return Response(html, headers={'Content-Type': 'text/html'})

# Connect to a network
@app.post('/connect')
async def connect_home_network(request):

    global last_valid_password
    ssid = request.json['wirelessClient']['ssid']
    password = request.json['wirelessClient']['password']

    if not ssid or not password:
        return { "error": "You must select a valid SSID and enter a password to continue." }, 500
    
    sta = network.WLAN(network.STA_IF)
    # Activate interface first, then set the hostname.
    sta.active(True)
    sta.config(dhcp_hostname="tinklink")
    
    if sta.isconnected():
        sta.disconnect()
        await asyncio.sleep(1)
    
    try:
        sta.connect(ssid, password)
    except Exception as e:
        return { "error": f"Error during connect: {e}" }, 500
    
    timeout = 10
    while timeout > 0 and not sta.isconnected():
        await asyncio.sleep(1)
        timeout -= 1
    
    if sta.isconnected():
        last_valid_password = password
        message = "Connected"

        # Attempt to save the connection on first connect attempt
        try:
            data = config.get_config()
            data["wirelessClient"] = request.json["wirelessClient"]
            config.write_config(data)
            return { "ok": "Connection saved." }
        except OSError as e:
            print(f"Failed to save connection (OS Error): {e}")
            return { "error": f"Failed to save connection (OS Error): {e}" }, 500
        except Exception as e:
            print(f"Failed to save connection (OS Error): {e}")
            return { "error": f"Failed to save connection: {e}" }, 500
    else:
        # Attempt to fall back to the previously saved connection if available
        try:
            print("Attempt fallback")
            data = config.get_config()

            saved_ssid = data["wirelessClient"]["ssid"]
            saved_password = data["wirelessClient"]["password"]
            
        except OSError:
            saved_ssid = None
            saved_password = None
        
        if saved_ssid and saved_ssid == ssid:
            print("Attempting fallback connection using saved credentials.")
            sta.disconnect()
            await asyncio.sleep(1)
            sta.connect(saved_ssid, saved_password)
            fallback_timeout = 10
            while fallback_timeout > 0 and not sta.isconnected():
                await asyncio.sleep(1)
                fallback_timeout -= 1
            if sta.isconnected():
                last_valid_password = saved_password
                message = "Connected using saved credentials"
            else:
                message = "WiFi Connection Failed (Check Password)"
                sta.disconnect()
                await asyncio.sleep(1)
                sta.active(False)
                await asyncio.sleep(1)
                sta.active(True)
                sta.config(dhcp_hostname="tinklink")

                return { "error": message}, 500
        else:
            message = "WiFi Connection Failed (Check Password)"
            sta.disconnect()
            await asyncio.sleep(1)
            sta.active(False)
            await asyncio.sleep(1)
            sta.active(True)
            sta.config(dhcp_hostname="tinklink")

            return { "error": message}, 500

        return { "ok": message }

# Disconnect from a network
@app.post('/disconnect')
async def disconnect_home_network(request):
    print("calling disconnect")
    sta = network.WLAN(network.STA_IF)
    if sta.isconnected():
        sta.disconnect()
        await asyncio.sleep(1)
    timeout = 5
    while timeout > 0 and sta.isconnected():
        await asyncio.sleep(1)
        timeout -= 1

    message = "Disconnected" if not sta.isconnected() else "Disconnect failed. Please try again."
    return json.dumps({ "ok": message }), 200, {'Content-Type': 'application/json' }

# Save connection details
@app.post('/save_connection')
async def save_connection(request):
    credentials = request.json

    if not credentials["network_name"] or not credentials["password"]:
        # code 400?, should be 500?
        return { "error": "Missing network name or password" }
    try:
        data = config.get_config()
        data["wirelessClient"] = request.json
        config.write_config(data)

        return { "ok": "Connection Saved" }
    except OSError as e:
        return { "error": f"Failed to save connection {e}" }, 500
    except Exception as e:
        return { "error": f"Failed to save connection {e}" }, 500

# Delete saved connection details
@app.post('/delete_connection')
async def delete_connection(request):
    try:
        data = config.get_config()
        data["wirelessClient"] = None
        config.write_config(data)
        return { "ok": "Saved Connection Deleted" }
    except OSError as e:
        return { "error": f"Error Deleting Saved Connection: str{e}" }, 500

@app.errorhandler(404)
def not_found(request):
    return Response(status_code=302, headers={'Location': '/remote-page'})
    
def start_web_server():
    global pubsub_terminal_origin
    global terminal_websockets
    pubsub_terminal_origin = PubSub.create_origin("terminal")
    terminal_websockets = set()
    
    global pubsub_remote_origin
    global remote_websockets
    pubsub_remote_origin = PubSub.create_origin("remote")
    remote_websockets = set()

    getPubSub().subscribe("/*", _on_message_terminal, pubsub_terminal_origin)

    # Start both the web server and the UART loopback reader concurrently.
    server_task = asyncio.create_task(app.start_server(host='0.0.0.0', port=80))#, debug=True))
    return server_task
