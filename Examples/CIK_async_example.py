# Import basics
import board
import digitalio
import time
import asyncio

# Get WiFi credentials from secrets.py
from secrets import secrets

# Import ESP32 dependencies (for wifi)
import busio
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_socketpool


# Define & initialize ESP32 connection pins
esp32_cs = digitalio.DigitalInOut(board.D9)
esp32_ready = digitalio.DigitalInOut(board.D11)
esp32_reset = digitalio.DigitalInOut(board.D12)

# Define ESP32 connection
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)


# Check if there is an esp32 module attached and what its firmware version is
if esp.status == adafruit_esp32spi.WL_IDLE_STATUS:
    print("\nESP32 WiFi Module found.")
    print("Firmware version:", str(esp.firmware_version, "utf-8"))
    print("*" * 40)

# Check if the right network available, and if not, shut down.
print("\nScanning for available networks...\n")


network_list = []
for ap in esp.scan_networks():
    network_list.append(str(ap.ssid, "utf-8"))
print(network_list)

if secrets["ssid"] not in network_list:
    print(secrets["ssid"], "not found. \nAvailable networks:", network_list)
    raise SystemExit(0)

# Try to connect to the right network
print(secrets["ssid"], "found. Connecting...")
while not esp.is_connected:
    try:
        esp.connect_AP(secrets["ssid"], secrets["password"])
    except (RuntimeError, ConnectionError, OSError) as e:
        print("\nUnable to establish connection. Are you using a valid password?")
        print("Error message:", e, "\nRetrying...")
        continue

# When a network is found, the esp will reply with its ip address
print("Connected! IP address:", esp.pretty_ip(esp.ip_address))

def receiveEvent(sender, recipient, event):
    print('from ', sender, ' -> ', event)

# Import oocsi
from oocsi import OOCSI

oocsi = OOCSI("/test/diede/Connected_Interaction_Kit_##", "gimme.oocsi.net", esp)
oocsi.subscribe("testchannel", receiveEvent)
# after connecting to the wifi the main loop starts which checks its connection to DataFoundry
led = digitalio.DigitalInOut(board.D13)
led.direction = digitalio.Direction.OUTPUT

async def blink():
    while True:
        led.value = True
        await asyncio.sleep(1)
        led.value = False
        await asyncio.sleep(1)


async def loop():

    asyncio.create_task(blink())
    await oocsi.keepAlive()



asyncio.run(loop())
