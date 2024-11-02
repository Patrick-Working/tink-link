from microdot import Microdot, Response
from machine import UART, Pin
import network

# Configure UART for 8-N-1, 9600 baud
uart = UART(0, baudrate=9600, bits=8, parity=None, stop=1, tx=Pin(0), rx=Pin(1))

# Set up LED for testing feedback
led = Pin("LED", Pin.OUT)

# Set up Access Point mode
ap = network.WLAN(network.AP_IF)
ap.config(essid='Tink Link', password='12345678')
ap.active(True)

print("Access Point Active. Connect to 'Tink Link'")
print("AP IP address:", ap.ifconfig()[0])

# Initialize the Microdot app
app = Microdot()
Response.default_content_type = 'text/html'

# Command history and timestamp
command_history = []
timestamp = 0

# Main HTML page
def generate_html():
    history_html = ''.join(f'<li>{cmd}</li>' for cmd in reversed(command_history))
    return f"""<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="/skeleton.css">
    <title>Tink Link</title>
</head>
<body>
<h3 style="padding: 0; margin: 0;">Tink Link</h3>
Serial over HTTP for the RetroTINK-4K
<br><br>
    <form action="/" method="post">
        <label for="command">Enter Command:</label>
        <input type="text" id="command" name="command" required>
        <button type="submit">Send</button>
    </form>
    
    <h4 style="padding: 0; margin: 0;">Command History:</h4>
    <ul style="border: 1px solid black; padding: 10px; border-radius: 5px;">
        {history_html}
    </ul>
    <footer>
        <center><a href="/help">Click Here for help or more information.</a><br>Tink Link created by <a href="oldkid.net">Old Kid</a>. </center>
    </footer>
</body>
</html>
"""
# Help page HTML
def generate_help_html():
    return """<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/skeleton.css">
    <title>Tink Link Help</title>
</head>
<body>
    <h3>About Tink Link</h3>
    <p>The Tink Link uses a Raspberry Pi Pico W to send serial communication commands to the RetroTINK-4K. This can currently used to replicate remote control commands, with the possibly of other features down the line. How it works:<br>
    Using a Wi-Fi-enabled smart device or computer, you connect to a locally hosted hot spot created by the Pico W. Once connected, navigating to the Tink Link web page will give you the option to enter serial terminal commands. The Pico translates submitted text commands to a GPIO data transmission pin. This pin uses "open drain" 3.3V signaling logic which, when interfaced to the HD15 data input of the RetroTINK-4K, can simulate Remote Control inputs. Reply data from the RetroTINK-4K are also received on an additional Pico GPIO pin.</p>
    <p>For a list of accepted commands, please visit: <a href="https://consolemods.org/wiki/AV:RetroTINK-4K" target="_blank">https://consolemods.org/wiki/AV:RetroTINK-4K</a></p>
    <footer>
        <center><br>Tink Link created by <a href="oldkid.net">Old Kid</a>.</center>
    </footer>
</body>
</html>
"""

# Serve main page and handle command submission
@app.route('/', methods=['GET', 'POST'])
def index(request):
    global timestamp
    if request.method == 'POST':
        command = request.form.get('command', '')
    if command:
        led.on()
        uart.write(command + " \r\n")  # Send the command with \r\n appended
        print(f"Sent command: {command}\\r\\n")
        # Log with \r\n and styled "Sent" in green italics
        command_history.append(f"[{timestamp % 256}] <span style='color: green; font-style: italic;'>Sent:</span> {command} \\r\\n")

        if uart.any():
            response = uart.read().decode('utf-8').strip()
            print(f"Received: {response}")
            # Log response with styled "Received" in red italics
            command_history.append(f"[{timestamp % 256}] <span style='color: red; font-style: italic;'>Received:</span> {response}")

        led.off()
        timestamp += 1


    return generate_html(), {'Content-Type': 'text/html'}

# Help page route
@app.route('/help')
def help_page(request):
    return generate_help_html(), {'Content-Type': 'text/html'}

# Route to serve CSS from the file system
@app.route('/skeleton.css')
def serve_css(request):
    try:
        with open('skeleton.css', 'r') as file:
            css_content = file.read()
        return Response(css_content, headers={'Content-Type': 'text/css'})
    except OSError:
        return Response("/* CSS file not found */", headers={'Content-Type': 'text/css'})


# Start the Microdot server
app.run(host="0.0.0.0", port=80)

