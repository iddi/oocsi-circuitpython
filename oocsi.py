# Copyright (c) 2025 Mathias Funk
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php

import wifi
import socketpool
import time
import json
import random
import asyncio

__author__ = 'matsfunk'


class OOCSI:
    """
    OOCSI class for managing communication with an OOCSI server.
    """

    def __init__(self, handle=None, host='localhost', port=4444, callback=None):
        """
        Initializes the OOCSI client and connects to the server.

        Args:
            handle (str): Unique identifier for the client. Defaults to None.
            host (str): Server hostname. Defaults to 'localhost'.
            port (int): Server port. Defaults to 4444.
            callback (function): Callback function to handle received messages. Defaults to None.
        """
        if handle is None or len(handle.strip()) == 0:
            handle = "OOCSIClient_####"
        while "#" in handle:
            handle = handle.replace("#", str(random.randrange(10)), 1)
        self.handle = handle

        self.receivers = {self.handle: [callback]}
        self.calls = {}
        self.services = {}
        self.reconnect = True
        self.connected = False

        # Connect the socket to the port where the server is listening
        self.server_address = (host, port)
        self.log('connecting to %s port %s' % self.server_address)
        self.init()

        # Block till we are connected
        while not self.connected:
            time.sleep(0.2)

    def init(self):
        """
        Initializes the socket connection to the OOCSI server.
        """
        try:
            # Create a socket pool
            pool = socketpool.SocketPool(wifi.radio)

            # Create a TCP/IP socket
            self.sock = pool.socket(type=pool.SOCK_STREAM, proto=pool.IPPROTO_TCP)

            # Connect to the server
            self.sock.connect(self.server_address)

            try:
                # Send initial data to establish connection
                message = self.handle + '(JSON)'
                self.internalSend(message)

                try:
                    # Receive the server response
                    buffer = bytearray(1024)
                    received_bytes = self.sock.recv_into(buffer)
                    data = buffer[:received_bytes].decode('utf-8')
                except:
                    pass

                if data.startswith('{'):
                    self.log('connection established')
                    # Re-subscribe to channels
                    for channelName in self.receivers:
                        self.internalSend('subscribe {0}'.format(channelName))
                    self.connected = True
                    self.sock.setblocking(False)
                    self.sock.settimeout(0)
                elif data.startswith('error'):
                    self.log(data)
                    self.reconnect = False

            finally:
                pass
        except:
            pass

    def log(self, message):
        """
        Logs a message with the client's handle.

        Args:
            message (str): Message to log.
        """
        print('[{0}]: {1}'.format(self.handle, message))

    def internalSend(self, msg):
        """
        Sends a message to the server.

        Args:
            msg (str): Message to send.
        """
        try:
            self.sock.sendall((msg + '\n').encode())
        except:
            self.connected = False

    def check(self):
        """
        Checks for incoming messages from the server and processes them.
        """
        try:
            buffer = bytearray(1024)
            received_bytes = self.sock.recv_into(buffer)
            data = buffer[:received_bytes].decode('utf-8')
            lines = data.split("\n")
            for line in lines:
                if len(data) == 0:
                    self.sock.close()
                    self.connected = False
                elif line.startswith('ping') or line.startswith('.'):
                    self.internalSend('.')
                elif line.startswith('{'):
                    self.receive(json.loads(line))
        except:
            pass

    async def asyncCheck(self):
        """
        Asynchronously checks for incoming messages from the server and processes them.
        """
        try:
            buffer = bytearray(1024)
            try:
                # Create asynchronous task to check for new messages
                socket_task = asyncio.create_task(self._recv_into(buffer))
                received_bytes = await socket_task
                
                if received_bytes == 0:  # Connection closed by peer
                    self.sock.close()
                    self.connected = False
                    return
                
                data = buffer[:received_bytes].decode('utf-8')
                lines = data.split("\n")
                for line in lines:
                    if line.startswith('ping') or line.startswith('.'):
                        self.internalSend('.')
                    elif line.startswith('{'):
                        self.receive(json.loads(line))
            except OSError as e:
                if e.args[0] == 11:  # EAGAIN error
                    pass  # No data available right now, that's okay
                else:
                    raise  # Re-raise other OSError types
            except ConnectionError:
                self.sock.close()
                self.connected = False
        except Exception as e:
            self.log(f"Error in check: {str(e)}")
            pass

    async def _recv_into(self, buffer):
        """
        Helper method to handle socket receive operations asynchronously.
        """
        return self.sock.recv_into(buffer)
    
    def receive(self, event):
        """
        Processes a received event message.

        Args:
            event (dict): Event data received from the server.
        """
        sender = event['sender']
        recipient = event['recipient']

        # Clean up the event data
        del event['recipient']
        del event['sender']
        del event['timestamp']
        if 'data' in event:
            del event['data']

        if '_MESSAGE_HANDLE' in event and event['_MESSAGE_HANDLE'] in self.services:
            service = self.services[event['_MESSAGE_HANDLE']]
            del event['_MESSAGE_HANDLE']
            service(event)
            self.send(sender, event)
            self.receiveChannelEvent(sender, recipient, event)

        else:
            if '_MESSAGE_ID' in event:
                myCall = self.calls[event['_MESSAGE_ID']]
                if myCall['expiration'] > time.time():
                    response = self.calls[event['_MESSAGE_ID']]
                    response['response'] = event
                    del response['expiration']
                    del response['_MESSAGE_ID']
                    del response['response']['_MESSAGE_ID']
                else:
                    del self.calls[event['_MESSAGE_ID']]

            else:
                self.receiveChannelEvent(sender, recipient, event)

    def receiveChannelEvent(self, sender, recipient, event):
        """
        Handles an event received on a specific channel by invoking the registered callbacks.

        Args:
            sender (str): Sender of the message.
            recipient (str): Recipient channel.
            event (dict): Event data.
        """
        if recipient in self.receivers and self.receivers[recipient] is not None:
            for x in self.receivers[recipient]:
                x(sender, recipient, event)

    def send(self, channelName, data):
        """
        Sends a message to a specific channel.

        Args:
            channelName (str): Name of the channel to send the message to.
            data (dict): Data to send.
        """
        self.internalSend('sendraw {0} {1}'.format(channelName, json.dumps(data)))

    def call(self, channelName, callName, data, timeout=1):
        """
        Sends a call message to a specific channel and waits for a response.

        Args:
            channelName (str): Name of the channel to send the call to.
            callName (str): Name of the call.
            data (dict): Data to send.
            timeout (int): Timeout for the call in seconds. Defaults to 1.

        Returns:
            dict: Response data.
        """
        data['_MESSAGE_HANDLE'] = callName
        data['_MESSAGE_ID'] = self.uuid4()
        self.calls[data['_MESSAGE_ID']] = {
            '_MESSAGE_HANDLE': callName,
            '_MESSAGE_ID': data['_MESSAGE_ID'],
            'expiration': time.time() + timeout
        }
        self.send(channelName, data)
        return self.calls[data['_MESSAGE_ID']]

    def callAndWait(self, channelName, callName, data, timeout=1):
        """
        Sends a call message to a specific channel and waits for a response within the specified timeout.

        Args:
            channelName (str): Name of the channel to send the call to.
            callName (str): Name of the call.
            data (dict): Data to send.
            timeout (int): Timeout for the call in seconds. Defaults to 1.

        Returns:
            dict: Response data.
        """
        call = self.call(channelName, callName, data, timeout)
        expiration = time.time() + timeout
        while time.time() < expiration:
            time.sleep(0.1)
            if 'response' in call:
                break

        return call

    def register(self, channelName, callName, callback):
        """
        Registers a callback for a specific call on a channel.

        Args:
            channelName (str): Name of the channel.
            callName (str): Name of the call.
            callback (function): Callback function to handle the call.
        """
        self.services[callName] = callback
        self.internalSend('subscribe {0}'.format(channelName))
        self.log('registered responder on {0} for {1}'.format(channelName, callName))

    def subscribe(self, channelName, f):
        """
        Subscribes to a channel with a callback function.

        Args:
            channelName (str): Name of the channel to subscribe to.
            f (function): Callback function to handle received messages.
        """
        if channelName in self.receivers:
            self.receivers[channelName].append(f)
        else:
            self.receivers[channelName] = [f]
        self.internalSend('subscribe {0}'.format(channelName))
        self.log('subscribed to {0}'.format(channelName))

    def unsubscribe(self, channelName):
        """
        Unsubscribes from a channel.

        Args:
            channelName (str): Name of the channel to unsubscribe from.
        """
        del self.receivers[channelName]
        self.internalSend('unsubscribe {0}'.format(channelName))
        self.log('unsubscribed from {0}'.format(channelName))

    def variable(self, channelName, key):
        """
        Creates an OOCSIVariable for a specific channel and key.

        Args:
            channelName (str): Name of the channel.
            key (str): Key for the variable.

        Returns:
            OOCSIVariable: The created OOCSIVariable instance.
        """
        return OOCSIVariable(self, channelName, key)

    def stop(self):
        """
        Stops the OOCSI client and disconnects from the server.
        """
        self.reconnect = False
        self.internalSend('quit')
        self.sock.close()
        self.connected = False

    def handleEvent(self, sender, receiver, message):
        """
        Placeholder method for handling events. Can be overridden by subclasses.

        Args:
            sender (str): Sender of the message.
            receiver (str): Receiver of the message.
            message (dict): Message data.
        """
        {}

    @staticmethod
    def uuid4():
        """
        Generates a random UUID compliant with RFC 4122.

        Returns:
            str: Generated UUID.
        """
        random_bytes = bytearray(random.getrandbits(8) for _ in range(16))
        random_bytes[6] = (random_bytes[6] & 0x0F) | 0x40  # Set the version to 0100
        random_bytes[8] = (random_bytes[8] & 0x3F) | 0x80  # Set the variant to 10

        # Convert bytes to hex string without using ubinascii
        hex_string = ''.join(f'{byte:02x}' for byte in random_bytes)

        # Format the UUID
        return '-'.join((hex_string[0:8], hex_string[8:12], hex_string[12:16], hex_string[16:20], hex_string[20:32]))

    def returnHandle(self):
        """
        Returns the handle of the OOCSI client.

        Returns:
            str: Handle of the client.
        """
        return self.handle

    def heyOOCSI(self, custom_name=None):
        """
        Creates an OOCSIDevice with the client's handle or a custom name.

        Args:
            custom_name (str): Custom name for the OOCSIDevice. Defaults to None.

        Returns:
            OOCSIDevice: The created OOCSIDevice instance.
        """
        if custom_name is None:
            return OOCSIDevice(self, self.handle)
        else:
            return OOCSIDevice(self, custom_name)


class OOCSICall:
    """
    OOCSICall class represents a call made to an OOCSI server, containing metadata about the call.
    """

    def __init__(self, parent=None):
        """
        Initializes an OOCSICall instance.

        Args:
            parent (OOCSI): Parent OOCSI instance used to generate the UUID. Defaults to None.
        """
        self.uuid = parent.uuid4()  # Generate a unique identifier for the call using the parent's UUID generation method.
        self.expiration = time.time()  # Set the expiration timestamp to the current time.
        

class OOCSIVariable:
    """
    OOCSIVariable class represents a variable in an OOCSI channel, allowing for subscribing to updates and setting values.
    """

    def __init__(self, oocsi, channelName, key):
        """
        Initializes an OOCSIVariable instance and subscribes to the channel for updates.

        Args:
            oocsi (OOCSI): Reference to the OOCSI instance.
            channelName (str): Name of the channel.
            key (str): Key associated with the variable.
        """
        self.key = key
        self.channel = channelName
        oocsi.subscribe(channelName, self.internalReceiveValue)
        self.oocsi = oocsi
        self.value = None
        self.windowLength = 0
        self.values = []
        self.minvalue = None
        self.maxvalue = None
        self.sigma = None

    def get(self):
        """
        Retrieves the current value of the variable, applying smoothing if applicable.

        Returns:
            any: The current value or the smoothed value.
        """
        self.oocsi.check()
        if self.windowLength > 0 and len(self.values) > 0:
            return sum(self.values) / float(len(self.values))
        else:
            return self.value

    def set(self, value):
        """
        Sets the value of the variable, applying constraints and smoothing if applicable, and sends the value to the channel.

        Args:
            value (any): The value to set.
        """
        tempvalue = value
        if self.minvalue is not None and tempvalue < self.minvalue:
            tempvalue = self.minvalue
        elif self.maxvalue is not None and tempvalue > self.maxvalue:
            tempvalue = self.maxvalue
        elif self.sigma is not None:
            mean = self.get()
            if mean is not None:
                if abs(mean - tempvalue) > self.sigma:
                    if mean - tempvalue > 0:
                        tempvalue = mean - self.sigma / float(len(self.values))
                    else:
                        tempvalue = mean + self.sigma / float(len(self.values))

        if self.windowLength > 0:
            self.values.append(tempvalue)
            self.values = self.values[-self.windowLength:]
        else:
            self.value = tempvalue
        self.oocsi.send(self.channel, {self.key: value})

    def internalReceiveValue(self, sender, recipient, data):
        """
        Internal method to handle received values from the channel.

        Args:
            sender (str): Sender of the message.
            recipient (str): Recipient of the message.
            data (dict): Data received from the channel.
        """
        if self.key in data:
            tempvalue = data[self.key]
            if self.minvalue is not None and tempvalue < self.minvalue:
                tempvalue = self.minvalue
            elif self.maxvalue is not None and tempvalue > self.maxvalue:
                tempvalue = self.maxvalue
            elif self.sigma is not None:
                mean = self.get()
                if mean is not None:
                    if abs(mean - tempvalue) > self.sigma:
                        if mean - tempvalue > 0:
                            tempvalue = mean - self.sigma / float(len(self.values))
                        else:
                            tempvalue = mean + self.sigma / float(len(self.values))

            if self.windowLength > 0:
                self.values.append(tempvalue)
                self.values = self.values[-self.windowLength:]
            else:
                self.value = tempvalue

    def min(self, minvalue):
        """
        Sets the minimum value constraint for the variable.

        Args:
            minvalue (any): Minimum value.

        Returns:
            OOCSIVariable: The current instance for chaining.
        """
        self.minvalue = minvalue
        if self.value < self.minvalue:
            self.value = self.minvalue
        return self

    def max(self, maxvalue):
        """
        Sets the maximum value constraint for the variable.

        Args:
            maxvalue (any): Maximum value.

        Returns:
            OOCSIVariable: The current instance for chaining.
        """
        self.maxvalue = maxvalue
        if self.value > self.maxvalue:
            self.value = self.maxvalue
        return self

    def smooth(self, windowLength, sigma=None):
        """
        Configures smoothing for the variable by setting the window length and optional sigma value.

        Args:
            windowLength (int): Length of the window for smoothing.
            sigma (float): Allowed deviation for smoothing. Defaults to None.

        Returns:
            OOCSIVariable: The current instance for chaining.
        """
        self.windowLength = windowLength
        self.sigma = sigma
        return self


class OOCSIDevice:
    """
    OOCSIDevice class represents a device in the OOCSI network, allowing for managing properties, locations, and components of the device.
    """

    def __init__(self, OOCSI, device_name: str) -> None:
        """
        Initializes an OOCSIDevice instance and logs its creation.

        Args:
            OOCSI (OOCSI): Reference to the OOCSI instance.
            device_name (str): Name of the device.
        """
        self._device_name = device_name
        self._device = {self._device_name: {}}
        self._device[self._device_name]["properties"] = {}
        self._device[self._device_name]["properties"]["device_id"] = OOCSI.returnHandle()
        self._device[self._device_name]["components"] = {}
        self._device[self._device_name]["location"] = {}
        self._components = self._device[self._device_name]["components"]
        self._oocsi = OOCSI
        self._oocsi.log(f'Created device {self._device_name}.')

    def addProperty(self, properties: str, propertyValue):
        """
        Adds a property to the device and logs the addition.

        Args:
            properties (str): Name of the property.
            propertyValue (any): Value of the property.

        Returns:
            OOCSIDevice: The current instance for chaining.
        """
        self._device[self._device_name]["properties"][properties] = propertyValue
        self._oocsi.log(f'Added {properties} to the properties list of device {self._device_name}.')
        return self

    def addLocation(self, location_name: str, latitude: float = 0, longitude: float = 0):
        """
        Adds a location to the device and logs the addition.

        Args:
            location_name (str): Name of the location.
            latitude (float): Latitude of the location. Defaults to 0.
            longitude (float): Longitude of the location. Defaults to 0.

        Returns:
            OOCSIDevice: The current instance for chaining.
        """
        self._device[self._device_name]["location"][location_name] = [latitude, longitude]
        self._oocsi.log(f'Added {location_name} to the locations list of device {self._device_name}.')
        return self

    def addSensor(self, sensor_name: str, sensor_channel: str, sensor_type: str, sensor_unit: str, sensor_default: float, mode: str = "auto", step: float = None, icon: str = None):
        """
        Adds a sensor component to the device and logs the addition.

        Args:
            sensor_name (str): Name of the sensor.
            sensor_channel (str): Channel associated with the sensor.
            sensor_type (str): Type of the sensor.
            sensor_unit (str): Unit of the sensor value.
            sensor_default (float): Default value of the sensor.
            mode (str): Mode of the sensor. Defaults to "auto".
            step (float): Step value for the sensor. Defaults to None.
            icon (str): Icon representing the sensor. Defaults to None.

        Returns:
            OOCSIDevice: The current instance for chaining.
        """
        self._components[sensor_name] = {}
        self._components[sensor_name]["channel_name"] = sensor_channel
        self._components[sensor_name]["type"] = "sensor"
        self._components[sensor_name]["sensor_type"] = sensor_type
        self._components[sensor_name]["unit"] = sensor_unit
        self._components[sensor_name]["value"] = sensor_default
        self._components[sensor_name]["mode"] = mode
        self._components[sensor_name]["step"] = step
        self._components[sensor_name]["icon"] = icon
        self._device[self._device_name]["components"][sensor_name] = self._components[sensor_name]
        self._oocsi.log(f'Added {sensor_name} to the components list of device {self._device_name}.')
        return self

    def addNumber(self, number_name: str, number_channel: str, number_min_max, number_unit: str, number_default: float, icon: str = None):
        """
        Adds a number component to the device and logs the addition.

        Args:
            number_name (str): Name of the number component.
            number_channel (str): Channel associated with the number component.
            number_min_max (tuple): Minimum and maximum values for the number component.
            number_unit (str): Unit of the number value.
            number_default (float): Default value of the number component.
            icon (str): Icon representing the number component. Defaults to None.

        Returns:
            OOCSIDevice: The current instance for chaining.
        """
        self._components[number_name] = {}
        self._components[number_name]["channel_name"] = number_channel
        self._components[number_name]["min_max"] = number_min_max
        self._components[number_name]["type"] = "number"
        self._components[number_name]["unit"] = number_unit
        self._components[number_name]["value"] = number_default
        self._components[number_name]["icon"] = icon
        self._device[self._device_name]["components"][number_name] = self._components[number_name]
        self._oocsi.log(f'Added {number_name} to the components list of device {self._device_name}.')
        return self

    def addBinarySensor(self, sensor_name: str, sensor_channel: str, sensor_type: str, sensor_default: bool = False, icon: str = None):
        """
        Adds a binary sensor component to the device and logs the addition.

        Args:
            sensor_name (str): Name of the binary sensor.
            sensor_channel (str): Channel associated with the binary sensor.
            sensor_type (str): Type of the binary sensor.
            sensor_default (bool): Default state of the binary sensor. Defaults to False.
            icon (str): Icon representing the binary sensor. Defaults to None.

        Returns:
            OOCSIDevice: The current instance for chaining.
        """
        self._components[sensor_name] = {}
        self._components[sensor_name]["channel_name"] = sensor_channel
        self._components[sensor_name]["type"] = "binary_sensor"
        self._components[sensor_name]["sensor_type"] = sensor_type
        self._components[sensor_name]["state"] = sensor_default
        self._components[sensor_name]["icon"] = icon
        self._device[self._device_name]["components"][sensor_name] = self._components[sensor_name]
        self._oocsi.log(f'Added {sensor_name} to the components list of device {self._device_name}.')
        return self

    def addSwitch(self, switch_name: str, switch_channel: str, switch_default: bool = False, icon: str = None):
        """
        Adds a switch component to the device and logs the addition.

        Args:
            switch_name (str): Name of the switch.
            switch_channel (str): Channel associated with the switch.
            switch_default (bool): Default state of the switch. Defaults to False.
            icon (str): Icon representing the switch. Defaults to None.

        Returns:
            OOCSIDevice: The current instance for chaining.
        """
        self._components[switch_name] = {}
        self._components[switch_name]["channel_name"] = switch_channel
        self._components[switch_name]["type"] = "switch"
        self._components[switch_name]["state"] = switch_default
        self._components[switch_name]["icon"] = icon
        self._device[self._device_name]["components"][switch_name] = self._components[switch_name]
        self._oocsi.log(f'Added {switch_name} to the components list of device {self._device_name}.')
        return self

    def addLight(self, light_name: str, light_channel: str, led_type: str, spectrum, light_default_state: bool = False, light_default_brightness: int = 0, mired_min_max = None, icon: str = None):
        """
        Adds a light component to the device and logs the addition.

        Args:
            light_name (str): Name of the light.
            light_channel (str): Channel associated with the light.
            led_type (str): Type of LED.
            spectrum (str): Spectrum of the light.
            light_default_state (bool): Default state of the light. Defaults to False.
            light_default_brightness (int): Default brightness of the light. Defaults to 0.
            mired_min_max (tuple): Minimum and maximum mired values. Defaults to None.
            icon (str): Icon representing the light. Defaults to None.

        Returns:
            OOCSIDevice: The current instance for chaining.
        """
        SPECTRUM = ["WHITE", "CCT", "RGB"]
        LEDTYPE = ["RGB", "RGBW", "RGBWW", "CCT", "DIMMABLE", "ONOFF"]

        self._components[light_name] = {}
        if led_type in LEDTYPE:
            if spectrum in SPECTRUM:
                self._components[light_name]["spectrum"] = spectrum
            else:
                self._oocsi.log(f'error, {light_name} spectrum does not exist.')
                pass
        else:
            self._oocsi.log(f'error, {light_name} ledtype does not exist.')
            pass

        self._components[light_name]["channel_name"] = light_channel
        self._components[light_name]["type"] = "light"
        self._components[light_name]["ledType"] = led_type
        self._components[light_name]["spectrum"] = spectrum
        self._components[light_name]["min_max"] = mired_min_max
        self._components[light_name]["state"] = light_default_state
        self._components[light_name]["brightness"] = light_default_brightness
        self._components[light_name]["icon"] = icon
        self._device[self._device_name]["components"][light_name] = self._components[light_name]
        self._oocsi.log(f'Added {light_name} to the components list of device {self._device_name}.')
        return self

    def submit(self):
        """
        Submits the device information to the OOCSI network by sending a message and logs the submission.
        """
        data = self._device
        self._oocsi.internalSend('sendraw {0} {1}'.format("heyOOCSI!", json.dumps(data)))
        self._oocsi.log(f'Sent heyOOCSI! message for device {self._device_name}.')

    def sayHi(self):
        """
        Alias for submit method to send the device information to the OOCSI network.
        """
        self.submit()
