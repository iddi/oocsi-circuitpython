import wifi
import time
import asyncio
from async_oocsi import OOCSI
from secrets import secrets

# connect to the WIFI
network = wifi.radio

# Create a task to check for incoming messages from the OOCSI server
async def checkMessages():
    while True:
        try:
            await o.check()
        except Exception as e:
            print(f"Error in checkMessages: {str(e)}")
        await asyncio.sleep(0.2)

# Create a task to send messages to the OOCSI server
async def sendMessages():
    while True:
        o.send('CircuitPython/tutorial', {'message': 'Hello from CircuitPython!'})
        await asyncio.sleep(0.5)

# Print event information
def printMessage(sender, recipient, event):
    print('from ', sender, ' -> ', event)

# Connect to the WiFi network
def connectWifi():
    if network.connected == False:
        print('connecting to network...')
        # replace these by your WIFI name and password
        network.connect(secrets["ssid"], secrets["password"])
        while network.connected == False:
            pass
    # print('network config:', wlan.ifconfig())

#---------------------------------------------------------------------------

# Connect to wifi
connectWifi()

# Connect to OOCSI:
o = OOCSI('CircuitPython/tutorial/receiver#', 'oocsi.id.tue.nl')

# Subscribe to 'testchannel' on the OOCSI server and print incomming messages
o.subscribe('testchannel', printMessage)

# keep the program running, can be quit with CTRL-C
async def main():   
    # Create tasks to check for incoming messages and send messages
    messages = asyncio.create_task(checkMessages())
    send_message = asyncio.create_task(sendMessages())

    # Run both tasks at the same time independently from eachother
    await asyncio.gather(messages, send_message)

# Run the main function
asyncio.run(main())