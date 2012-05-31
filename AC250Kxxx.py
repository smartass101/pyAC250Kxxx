#!/usr/bin/python2

"""Python wrapper and simple API for communication with a AC250Kxxx series Diametral power source

All communication is performed through the :class:`Device` class and it's methods, using the pySerial library
"""

from serial import Serial 

CTRLSUM = False

################################################################
################     HELPER FUNCTIONS           ################
################################################################

def _hexify(number):
    """_hexify(number) -> hexstring_repr
    
    Translates the number to an uppercase string representing it in hexadecimal.

    Parameters
    ----------
    number : int
        an integer, expected to be unsigned (negative values do not make sense in the scope of communication)

    Returns
    -------
    hexstring_repr : str
        the returned hexstring has no leading 'x' or '0x' and is always at least least two characters long (padding with leading '0')
        it is also uppercase

    See Also
    --------
    :func:`_unhexify` : inverse function
    """
    #if number <0 : number*=-1 #TODO not sure if useful
    code=hex(number)[2:] #cut off the '0x' part
    if number < 16 : #if the number as hexadecimal is < 16 the hex string will have just one char
        code="0"+code# the hexadecimal address must have two characters
    return code.upper() #return an uppercase string

def _unhexify(hexstring):
    """_unhexify(hexstring_repr) -> number
    
    Translate an uppercase string representing a hexadecimal number to the number in decimal.

    Parameters
    ----------
    hexstring_repr : str
        the hexadecimal string  should _not_ start with 'x' or '\\x' or anything similar, only leading '0x' is acceptable

    Returns
    -------
    number : int
        the number being represented by the hexstring

    See Also
    --------
    :func:`_hexify` : inverse function
    """
    return int(hexstring, 16) #return the number represented in hexadecimal

def _ctrl_sum(string):
    """_ctrl_sum(string) -> ctrl_sum_hexstring_repr

    Calculate the control sum of the provided uppercase string message as represented in hexadecimal.

    Parameters
    ----------
    string : str
        an uppercase string
        
    Returns
    -------
    ctrl_sum_hexstring_repr : str
        the sum as an uppercase string representing the control sum in hexadecimal
        always lesser or equal to 'FF' (256)

    Note
    ----
    The AC250Kxxx communication specification requires that the control sum is lesser or equal to 256 ('FF'), therefore 256 is substracted from the sum if sum > 256.

    See Also
    --------
    :func:`_hexify`, :func:`_unhexify` : Hexstring representation of integers as required by the AC250Kxxx communication specification.
    """
    _sum=0
    for char in string:
        _sum += ord(char) #tranclate character to int
    while _sum > 256: #the sum must be lesser or equal to 256
        _sum -= 256
    return _hexify(_sum)

################################################################
################    MAIN CLASSES                ################
################################################################

class Device(Serial):
    """AC250Kxxx device communication wrapper class

    Provides access to the device on the specified address. Can be used to query or set various settings, e.g. voltage.
    
    Attributes
    ----------
    address : int
        address of the device
        ranges from 0 to 31, inclusive (32 possible addresses)
        address 255 is the broadcast address, any device accepts it, but won't send a response packet back (not recommended, makes debugging very hard)
        the device address can be displayed by holding the red 'Clear' button for several seconds

    Note
    ----
    The class is a subclass of :class:`serial.Serial` and as is required by the AC250Kxxx communication specification,
    it is initialized with a baudrate of 9600, bytesize of 8, no bit parity, 1 stopbit and no flow control
    """
    
    def __init__(self, address=255, serial_port=0):
        """Initialize a new Device object with the specified address communicating through the specified serial port.

        Parameters
        ----------
        address : int
            device address, see the :class:`Device` docstring for a better explanation
            ranges from 0 to 31 inclusive, defaluts to 255 (broadcast address)
        serial_port : int or str
            number of the serial port to be used for communication
            or the explicit name of the device to be passed to :meth:`serial.Serial.__init__`
            on Linux it's the number X in /dev/ttySX and defaults to 0 (/dev/ttyS0)
        """
        super(Device, self).__init__(serial_port, baudrate=9600, bytesize=8, parity='N', stopbits=1, xonxoff=False) #initialize the serial port as required by the specification
        self.address=address #store for later use TODO will it be used later at all? maybe just the hexaddress is enough. but the attribute is for informative purposes too
        self.hexaddress=_hexify(address) #store for usage in packet construction and recieved packets verification

    def send(self,message):
        """Construct a packet containing the message and send it to the Device

        The packet is an ANSI string composed of uppercase letters and special characters. The packet starts with the '@' initializer character, then the device address as a hexstring_repr as returned by :func:`_hexify`, then the actuall message as an uppercase string, then the hexstring_repr control sum of the previous characters as returned by :func:`_ctrl_sum` and finally ends with the CR (carriage return) character.
        Example : '@0ANAP100E1\r' is a packet for the device with address 10 (0x0a) with the message 'NAP100'. The control sum of the previous characters is 0xe1

        Parameters
        ----------
        message : str
            uppercase string to be sent in the packet
            at least 3 characters long

        Note
        ----
        The control sum is only calculated and appended if CTRLSUM is set to True
        """
        packet = '@' + self.hexaddress + message #start off with the initializer, add the address and message
        packet += _ctrl_sum(packet[1:]) #append the control sum
        packet += '\x0d' # and CR character
        self.write(packet) #send the packet
        for char in packet:
            print char,": ",hex(ord(char))

    def receive(self):
        """Receive a packet from the device and decode the message contained in that packet.

        The packet is similar to the packet constructed by :func:`Device.send`, but starts with a '#' character and may not be so long.
        The device address and the control sum in the packet are checked.

        Returns
        -------
        message : str
            uppercase string contained in the packet

        Raises
        ------
        :class:`ValueError`
            - when address of the :class:`Device` object does not correspond to the device address in the packet
            - if the control sum of the packet does not match the calculated one
            - when the packet is bad
        """
        packet = self.read(self.isWaiting()) #read in the number of bytes in the receive buffer
        if packet[0] != '#': #if the packet does not start properly
            raise ValueError("received packet does not start with '#'")
        elif packet[1:3] != self.hexaddress: #if the packet device address is wrong
            #the second and third character is the address
            raise ValueError("received packet from address '" + packet[1:3] + "' (hex), but our device has address '" + self.hexaddress + "' (hex)")
        elif CTRLSUM:
            if packet[-5:-3] != _ctrl_sum(packet[:-5]): #if the control sum in the packet does not match the real controlsum
                #the control sum are the last two characters before the CR char
                raise ValueError("received packet contains a wrong control sum '" + packet[-5:-3] + "' (hex), should be '" + _ctrl_sum(packet[:-5]) + "' (hex)")
        else: #verything seems to be ok
            if CTRLSUM:
                return packet[3:-5] #return only the message without control sum
            else:
                return packet[3:-3] #return message without ctrlsum

    def query(self,message):
        """query(message) -> response

        Query the device: send a message and get a response

        Parameters
        ----------
        message : str
        a message to be passed to :func:`Device.send`

        Returns
        -------
        response : str
            the response of the device
            on failure returns None

        Note
        ----
        The method first retries the query 3 times on failure
        """
        failures=0
        while failures < 4:
            try: #handle errors
                self.send(message)
                return self.receive()
            except ValueError:
                failures += 1
        return None #is we got beyond the while cycle we have 3 failures

    def set_voltage(self, voltage):
        """Set the voltage output of the device

        Parameters
        ----------
        voltage : int
            the voltage in [V], should be within the device range

        Returns
        -------
        real_voltage : int
            the device responds with the current set voltage

        Raises
        ------
        ValueError
            if the device responds that the requested voltage is beyond the possible range

        Todo
        ----
        * actually implement the error detection and raising
        * verify that the return value starts with 'NAP'
        """
        return int(self.query('NAP' + str(voltage))[3:]) #return the current voltage
        #the response starts with 'NAP'
        


        
