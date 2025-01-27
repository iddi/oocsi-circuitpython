# oocsi-circuitpython
OOCSI library for CircuitPython

## What is OOCSI?
OOCSI is a communication protocol developed at Eindhoven University of Technology aimed at making it as easy as possible for designers and researchers to connect their prototypes. OOCSI supports various languages and platforms and [Check this out if you want to learn more about OOCSI](https://oocsi.net).

## How to get started with OOCSI on Circuitpython
To get started with OOCSI on circuitpython, you first need a microcontroller that supports WiFi. Examples microcontrollers that have build in WiFi are boards based on the ESP32s2 and Pico-W chips. We assume you have already installed circuitpython on your microcontroller, but if you have not yet installed circuitpython, [Click here to read how to install Circuitpython onto your microcontroller](https://learn.adafruit.com/welcome-to-circuitpython/installing-circuitpython) When circuitpython is correctly installed on your microcontroller, it should show a new external drive in your file explorer named `CIRCUITPY`.

> [!NOTE]
> Some boards like the Connected Interaction Kit, Arduino Nano 2040 Connect, Arduino Uno R4 Wifi and Arduino Nano 33 IoT use a separate chip for WiFi and work a little differently [read more here, if you use one of these boards](/docs/ExternalWifiSetup.md)

### Instal the OOCSI library:
To instal the OOCSI library you need to download the OOCSI.py file and drag this into the `CIRCUITPY/lib/` folder of your microcontroller. After put the OOCSI.py file onto your microcontroller, the library should be installed correctly.

### Code
After having installed the OOCSI library we need to setup OOCSI so that it can reach the OOCSI server. OOCSI can be imported and set up with the following code:
```Python
# Import OOCSI
from oocsi import OOCSI

# Setup your OOCSI Connection
oocsi = OOCSI("circuitpython/tutorial/user##", "oocsi.id.tue.nl")
```
> [!TIP]
> For more information about setting up an oocsi connection [check here](/docs/OocsiCommands.md)

#### Connect to WiFi
For oocsi to work you also need a working internet connection, the following code connects you to the internet over wifi:
```Python
import wifi
from secrets import secrets

# Search for available networks
print("Available WiFi networks:")
for network in wifi.radio.start_scanning_networks():
    print("\t%s\t\tRSSI: %d\tChannel: %d" % (str(network.ssid, "utf-8"),network.rssi, network.channel))
wifi.radio.stop_scanning_networks()

# Connect to the desired WiFi networks
wifi.radio.connect(secrets["ssid"]), secrets["password"]))
```
Additional you should create a ["secrets.py"] file in the ["CIRCUITPY"] directory of your microcontroller, in which you store your WiFI credentials. 
> [!WARNING] 
> Don't share the secrets.py file with anyone, we dont want you to leak your own wifi password! [Click here to read more about secret files](/docs/SecretFiles.md)
```Python
secrets = {
    "ssid":"<network_ssid>",
    "password":"<WifiPassword>"
}
```

#### How to receive OOCSI messages
After you have configured your WiFi and OOCSI connection, it is time to start interacting with the OOCSI server. To receive OOCSI messages you can use the code below. you can now see messages appearing if you open the serial monitor.
```Python
# This is the function that is activated when the oocsi server sends a reply to your microcontroller. Every OOCSI message comes with a sender (Where the message comes from), a recipient (The destination of the message) and an event which contains the message itself
def receiveEvent(sender, recipient, event):
    # The following line prints out the Sender, Recipient and the Message
    print('from ', sender, ' -> ', event)

# The following line subscribes you to an oocsi channel; here "timechannel" is the oocsi channel, and "receiveEvent" the function that is started when a reply is received
oocsi.subscribe("timechannel", receiveEvent)
```

#### How to send OOCSI messages
To send OOCSI messages yourself, you use the send command. Put the following code snippet in your code and see your messages appear [here]()! Maybe even try to change the messageData to something else.

```Python
while true:
    messageData = "Hello World"
    oocsi.send("/circuitpython/tutorial", messageData)
```
