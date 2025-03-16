# OOCSI Asynchonous communication example
# This example on works on devices with an external esp32 module which works with esp32spi
# Example boards: RP2040 Nano Connect
# unchecked: Connected Interaction Kit, Lolin S3

# Import basics
import board
import digitalio
import asyncio

# Get WiFi credentials from secrets.py
from secrets import secrets

# Import ESP32 dependencies (for wifi)
import busio
from adafruit_esp32spi import adafruit_esp32spi

# Import oocsi
from oocsi_esp32spi import OOCSI

# Define led pins
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

# Define & initialize ESP32 connection pins
esp32_cs = digitalio.DigitalInOut(board.CS1)
esp32_ready = digitalio.DigitalInOut(board.ESP_BUSY)
esp32_reset = digitalio.DigitalInOut(board.ESP_RESET)

# Define ESP32 connection
# Secondary (SCK1) SPI used to connect to WiFi board on Arduino Nano Connect RP2040
spi = busio.SPI(board.SCK1, board.MOSI1, board.MISO1)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

# Function to run when an OOCSI message is received
def receiveEvent(sender, recipient, event):
    print('from ', sender, ' -> ', event)

# Check if there is an esp32 module attached and what its firmware version is
if esp.status == adafruit_esp32spi.WL_IDLE_STATUS:
    print("\nESP32 WiFi Module found.")
    print("Firmware version:", str(esp.firmware_version, "utf-8"))
    print("*" * 40)

# Try to connect to the right network
while not esp.is_connected:
    try:
        esp.connect_AP(secrets["ssid"], secrets["password"])
    except (RuntimeError, ConnectionError, OSError) as e:
        print("\nUnable to establish connection. Are you using a valid password?")
        print("Error message:", e, "\nRetrying...")
        continue

# When a network is found, the esp will reply with its ip address
print("Connected! IP address:", esp.pretty_ip(esp.ip_address))

# Initiate OOCSI connection
oocsi = OOCSI("/test/diede/Connected_Interaction_Kit_##", "hello.oocsi.net", esp)
oocsi.subscribe("testchannel", receiveEvent)

# Define an asynchronous blink function
async def blink():
    while True:
        led.value = True
        await asyncio.sleep(1)
        led.value = False
        await asyncio.sleep(1)

# Define loop
async def loop():
    asyncio.create_task(blink())
    await oocsi.keepAlive()

# Start loop
asyncio.core.run(loop())

