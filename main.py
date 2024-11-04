from microdot import Microdot, Response
from machine import UART, Pin
import network
import time
import gc

# Initialize UART0 with a baud rate of 9600
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

# Function to send a test message
def send_test_message():
    try:
        message = "remote menu\r\n"
        uart.write(message)
        print("Test Message sent:", message.strip())
    except Exception as e:
        print("Error sending test message:", e)

# Test function call outside request context to confirm UART
# send_test_message()

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

# Serve main page and handle command submission
@app.route('/', methods=['GET', 'POST'])
def index(request):
    global timestamp
    print("Memory before GC:", gc.mem_free())
    gc.collect()
    print("Memory after GC:", gc.mem_free())

    if request.method == 'POST':
        print("Request received - Processing POST")
        command = request.form.get('command', '').strip()
        print("Command entered:", command)
        
        if command:
            led.on()
            time.sleep(0.5)  # Keep LED on briefly to indicate command start
            
            try:
                # Attempt to send command over UART with exact formatting
                uart.write(command + "\r\n")
                print("Sent command:", command)
                
                # Log command with styled "Sent" in green italics
                command_history.append(f"[{timestamp % 256}] <span style='color: green; font-style: italic;'>Sent:</span> {command} \\r\\n")
                
                # Check for any response on UART and log it
                if uart.any():
                    response = uart.read().decode('utf-8').strip()
                    print("Received:", response)
                    command_history.append(f"[{timestamp % 256}] <span style='color: red; font-style: italic;'>Received:</span> {response}")
                
            except Exception as e:
                print("Error during UART communication:", e)
                command_history.append(f"<span style='color: red;'>Error:</span> {e}")
            
            led.off()
            timestamp += 1  # Increment timestamp after each command
            
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
