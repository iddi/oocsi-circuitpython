# oocsi-circuitpython
OOCSI library for CircuitPython

## Installation:
Installing the OOCSI library onto your circuitpython board is easy, download the OOCSI.py file and drag this into the folder "lib" in your device's CIRCUITPYTHON folder.

## Setting up OOCSI

### Devices with integrated WiFi support:
to use oocsi circuitpython on devices with integrated WiFi support all you first need to intialize a connection to the internet through the WiFi library:

#### Connect to WiFi
```Python
import wifi
from secrets import secrets

# Search for available networks
print("Available WiFi networks:")
for network in wifi.radio.start_scanning_networks():
    print("\t%s\t\tRSSI: %d\tChannel: %d" % (str(network.ssid, "utf-8"),
                                             network.rssi, network.channel))
wifi.radio.stop_scanning_networks()

# Connect to the desired WiFi networks
wifi.radio.connect(secrets["ssid"]), secrets["password"]))
```

with an additional "secrets.py" file in the "CIRCUITPY" directory, containing your wifi information. 
> [!WARNING] 
> Watchout with sharing the content of this file, we dont want you to leak your own wifi password!
```Python
secrets = {
    "ssid":"<network_ssid>",
    "password":"<WifiPassword>"
}
```

#### Connect to OOCSI

```Python
# Import OOCSI
from oocsi import OOCSI

# Setup your OOCSI Connection
# Here <YourOOCSIName> can be anything, aslong as its an unique name, by adding a "#" it will generate a random number. <oocsiURL> is the link to the oocsi server you want to use
oocsi = OOCSI("<YourOOCSIName>", "<oocsiURL>")
```

## Use OOCSI
After you have configured your wifi and oocsi connection, it is time to start interacting with the oocsi server. To receive oocsi messages you can use the following code
```Python
# This is the function that is activated when the oocsi server sends a reply to your microcontroller. Every OOCSI message comes with a sender (Where the message comes from), a recipient (The destination of the message) and an event which contains the message itself
def receiveEvent(sender, recipient, event):
    # The following line prints out the Sender, Recipient and the Message
    print('from ', sender, ' -> ', event)

# The following line subscribes you to an oocsi channel; here "timechannel" is the oocsi channel, and "receiveEvent" the function that is started when a reply is received
oocsi.subscribe("timechannel", receiveEvent)
```