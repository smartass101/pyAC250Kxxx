#!/usr/bin/python2

"""Python wrapper and simple API for communication with a AC250Kxxx series Diametral power source

All communication is performed through the :class:`Device` class and it's methods, using the pySerial library
"""

from serial import Serial
from time import sleep

################################################################
####                 CONSTANTS                              ####
################################################################

"""If True, verbosely print the packets, defaults to False"""
debug = False

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
    """
    #if number <0 : number*=-1 #TODO not sure if useful
    code=hex(number)[2:] #cut off the '0x' part
    if number < 16 : #if the number as hexadecimal is < 16 the hex string will have just one char
        code="0"+code# the hexadecimal address must have two characters
    return code.upper() #return an uppercase string

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
    :func:`_hexify` : Hexstring representation of integers as required by the AC250Kxxx communication specification.
    """
    _sum=0
    for char in string:
        _sum += ord(char) #tranclate character to int
    while _sum > 256: #the sum must be lesser or equal to 256
        _sum -= 256
    return _hexify(_sum)

def debug_maybe(packet):
    """debug_maybe(packet)

    If debug is True, print the representation of the packet and then its hexdump
    """
    if debug:
        print repr(packet)
        for char in packet:
            print char,": ",hex(ord(char))


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
    
    def __init__(self, address=255, serial_port=0, timeout=1.0):
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
        timeout : float, optional
            timeout in seconds for reading operations, defaults to 1 second
        """
        super(Device, self).__init__(serial_port, baudrate=9600, bytesize=8, parity='N', stopbits=1, xonxoff=False) #initialize the serial port as required by the specification
        self.address=address #store for later use TODO will it be used later at all? maybe just the hexaddress is enough. but the attribute is for informative purposes too
        self.hexaddress=_hexify(address) #store for usage in packet construction and recieved packets verification
        self.timeout = timeout

    def send(self, message):
        """Device.send(message)

        Construct a packet containing the message and send it to the Device

        The packet is an ANSI string composed of uppercase letters and special characters. The packet starts with the '@' initializer character, then the device address as a hexstring_repr as returned by :func:`_hexify`, then the actuall message as an uppercase string, then the hexstring_repr control sum of the previous characters as returned by :func:`_ctrl_sum` and finally ends with the CR (carriage return) character.
        Example : '@0ANAP100E1\r' is a packet for the device with address 10 (0x0a) with the message 'NAP100'. The control sum of the previous characters is 0xe1

        Parameters
        ----------
        message : str
            uppercase string to be sent in the packet
            at least 3 characters long
        """
        packet = '@' + self.hexaddress + message #start off with the initializer, add the address and message
        packet += _ctrl_sum(packet[1:]) #append the control sum
        debug_maybe(packet)
        packet += '\x0d' # and CR character
        self.write(packet) #send the packet
        
    def receive(self):
        """Device.receive() -> response

        Receive a packet from the device and decode the message contained in that packet.

        The packet is similar to the packet constructed by :meth:`Device.send`, but starts with a '#' character and does not contain a control sum.
        The initializing character and the device address are checked.

        Returns
        -------
        message : str
            uppercase string contained in the packet

        Raises
        ------
        :class:`ValueError`
            - when address of the :class:`Device` object does not correspond to the device address in the packet
        """
        current_char = bytearray(' ') #empty array to read into
        while current_char != "#": #wait for reply packet initializing character
            self.readinto(current_char)
        packet = current_char #initialize packet
        while current_char != "\r": #wait for packet terminating character
            self.readinto(current_char)
            packet.extend(current_char)
        packet = str(packet)
        debug_maybe(packet)
        if packet[1:3] != self.hexaddress: #if the packet device address is wrong
            #the second and third character is the address
            raise ValueError("received packet from address '" + packet[1:3] + "' (hex), but our device has address '" + self.hexaddress + "' (hex)")
        else: #verything seems to be ok
            return packet[3:-1] #return the message 

    def query(self,message):
        """Device.query(message) -> response

        Query the device: send a message and get a response

        Parameters
        ----------
        message : str
            a message to be passed to :meth:`Device.send`

        Returns
        -------
        response : str
            the response of the device
        """
        self.send(message)
        return self.receive()
            

    def command(self, instruction):
        """Device.command(instruction) -> ack

        Send a command to the device and wait for acknowledgment (ACK)
        Essentially just a wrapper around :meth:`Device.query`

        Parameters
        ----------
        same as for :meth:`Device.query`

        Returns
        -------
        ack : bool
            True if Device replied 'OK'
            False if Device replied 'Err'
            
        Raises
        ------
        :class:`RuntimeError`
            Raises if the reply was something else than 'OK' or 'Err'
        """
        ack = self.query(instruction)
        if ack == 'OK':
            return True
        elif ack == 'Err':
            return False
        else:
            raise RuntimeError("Device reported error: " + ack)
    
    def get_voltage(self):
        """Device.get_voltage() -> voltage

        Return the current set voltage in Volts

        Returns
        -------
        voltage : int
            current voltage in Volts
        """
        return int(self.query('NAP???')[3:]) #reply is 'NAPXXX'
    
    def set_voltage(self, voltage):
        """Device.set_voltage(voltage) -> success

        Set the voltage in Volts

        Parameters
        ----------
        voltage : int
            voltage to set in Volts

        Returns
        -------
        success : bool
            True if the command did succeed, False otherwise
        """
        return self.command('NAP%03d' % voltage) #it takes some time for the voltage to change

    voltage = property(fget=get_voltage, fset=set_voltage, doc="""Output voltage as an integer in Volts""")

    def get_output(self):
        """Device.get_output() -> status

        Return the current status of the output

        Returns
        -------
        status : bool
            True if output is activated, False otherwise
        """
        if self.query('OUT?')[-1] == '1': #should be 'OUT1'
            return True
        else: #should be 'OUT0'
            return False

    def set_output(self, status):
        """Device.set_output(status) -> success

        Set the status of the output

        Parameters
        ----------
        status : bool
            True if output should be activated, False otherwise
        
        Returns
        -------
        success : bool
            True if the command did succeed, False otherwise
        """
        if status: #if True
            return self.command('OUT1')
        else:
            return self.command('OUT0')
            
    output = property(fget=get_output, fset=set_output, doc="""Output status as a Boolean, True if activated, False otherwise""")
        
    def get_identification(self):
        """Device.get_identification() -> identification

        Return the identification of the device

        Returns
        -------
        identification : str
            name of the device, model and revision
        """
        return self.query('ID?')

    identification = property(fget=get_identification, doc="""Device identifiaction as a string""")
        
