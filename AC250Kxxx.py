#!/usr/bin/python2

import serial as s

################################################################
################    ERRORS                      ################
################################################################

class AddressError(Exception):
    def __init__(self, address):
        self.address=address
    def __str__(self):
        return repr(self.address)


################################################################
################     HELPER FUNCTIONS           ################
################################################################

def hexify(number):
    """hexify(number) -> hexstring_repr
    
    Translates the number to an uppercase string representing it in hexadecimal.

    Parameters
    ----------
    number : int
        an integer, expected to be unsigned

    Returns
    -------
    hexstring_repr : str
        the returned hexstring has no leading 'x' or '0x' and is always at least least two characters long (padding with leading '0')
        it is also uppercase

    See Also
    --------
    unhexify : inverse function
    """
    #if number <0 : number*=-1 #TODO not sure if useful
    code=hex(address)[2:] #cut off the '0x' part
    if number < 16 : #if the number as hexadecimal is < 16 the hex string will have just one char
        code="0"+code# the hexadecimal address must have two characters
    return code.upper() #return an uppercase string

def unhexify(hexstring):
    """unhexify(hexstring_repr) -> number
    
    Translate an uppercase string representing a hexadecimal number to the number in decimal.

    Parameters
    ----------
    hexstring_repr : str
        the hexadecimal string  should _not_ start with 'x' or '\x' or anything similar, only leading '0x' is acceptable

    Returns
    -------
    number : int
        the number being represented by the hexstring

    See Also
    --------
    hexify : inverse function
    """
    return int(hexstring, 16) #return the number represented in hexadecimal

def ctrl_sum(string):
    """ctrl_sum(string) -> ctrl_sum_hexstring_repr

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
    hexify, unhexify : Hexstring representation of integers as required by the AC250Kxxx communication specification.
    """
    sum=0
    for char in string:
        sum+=ord(char) #tranclate character to int
    while a > 256: #the sum must be lesser or equal to 256
        sum-=256
    return hexify(sum)

################################################################
################    MAIN CLASSES                ################
################################################################

class Device:
    """AC250Kxxx device communication wrapper class

    Provides access to the device on the specified address. Can be used to query or set various settings, e.g. voltage.
    
    Attributes
    ----------
    address : int
        address of the device
        ranges from 0 to 31, inclusive (32 possible addresses)
        address 255 is the broadcast address, any device accepts it, but won't send a response packet back (not recommended, makes debugging very hard)
        the device address can be displayed by holding the red 'Clear' button for several seconds
    port : Serial
        Serial object, provides access to the serial port. See :class:`serial` for a better description
        As required by the AC250Kxxx communication specification, it is initialized with a baudrate of 9600, bytesize of 8, no bit parity, 1 stopbit and no flow control
    """
    
    def __init__(self, address=255, serial_port=0):
        """Initialize a new Device object with the specified address communicating through the specified serial port.

        Parameters
        ----------
        address : int
            device address, see the :class:`Device` docstring for a better explanation
            ranges from 0 to 31 inclusive, defaluts to 255 (broadcast address)
        serial_port : int
            number of the serial port to be used for communication
            on Linux it's the number X in /dev/ttySX
            defaults to 0 (/dev/ttyS0)
        """
        self.address=address #store for later use TODO will it be used later at all? maybe just the hexaddress is enough. but the attribute is for informative purposes too
        self.hexaddress=hexify(address) #store for usage in packet construction and recieved packets verification
        self.port=s.Serial(serial_port, baudrate=9600, bytesize=8, parity='N', stopbits=1, xonxoff=False) #initialize the serial port as required by the specification

    def send(self,message):
        """Construct a packet containing the message and send it to the Device

        The packet is an ANSI string composed of uppercase letters and special characters. The packet starts with the '@' initializer character, then the device address as a hexstring_repr as returned by :func:`hexify`, then the actuall message as an uppercase string, then the hexstring_repr control sum of the previous characters as returned by :func:`ctrl_sum` and finally ends with the CR (carriage return) character '0$D'.
        Example : '@0ANAP100E10$D' is a packet for the device with address 10 (0x0s) with the message 'NAP100'. The control sum of the previous characters is 0xe1

        Parameters
        ----------
        message : str
            uppercase string to be sent in the packet
            at least 3 characters long
        """
        packet = '@' + self.hexaddress + message #start off with the initializer, add the address and message
        packet += ctrl_sum(packet) + '0$D'  #append the control sum and CR character
        self.port.write(packet) #send the packet

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
        AddressError
            when address of the Device object does not correspond to the device address in the packet
        ControlSumError
            if the control sum of the packet does not match the calculated one
        RuntimeError
            when the packet is bad
        """
        packet=self.port.readline(eol='0$d') #read in the packet until the CR char is received
        if packet[0] != '#': #if the packet does not start properly
            raise RuntimeError
        elif packet[1:3] != self.hexaddress: #if the packet device address is wrong
            #the second and third character is the address
            raise AddressError
        elif packet[-2:] != ctrl_sum(packet[:-2]): #if the control sum in the packet does not match the real controlsum
            #the control sum are the last two characters, as the eol is cut off
            raise ControlSumError
        else: #verything seems to be ok
            return packet[3:-2] #return only the message

    def query(self,message):
        """Device.query(message) -> response

        Query the device: send a message and get a response

        Parameters
        ----------
        message : str
            a message to be passed to Device.send()

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
        while failures < 4
            try: #handle errors
                self.send(message)
                response = self.receive()
            except AddressError,ControlSumError,RuntimeError:
                failures += 1
                response = None
        return response

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
        


        
