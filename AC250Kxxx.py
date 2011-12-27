#!/usr/bin/python2

import serial as s
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

    
class AddressError(Exception):
    def __init__(self, address):
        self.address=address
    def __str__(self):
        return repr(self.address)

class CommunicationString:
    """general communication string container

    each communication string consists of several parts described in Attributes
    initial : str
        the initial character
        determines the start of the packet
        '@' for a command packet
        '#' for a reply packet
        message : str
        the message contained by the packet
        
    """

    def __str__(self):
        """string representation of this object -> raw communication string"""
        return self.string
    def encode_string(self):
        """encode the raw string based on object attributes"""
        self.string=self.initial #the string starts with an initial character
        self.string+=self.encode_address() #add the address
        self.string+=self.message #add the message
        self.string+=self.parameters #add the message parameters
        self.string+=self.sum() #add the control sum
        self.string+=self.cr #end with the carriage return character
        
class CommandString(CommunicationString):
    """general command string for Diametral AC250K2D communication
    """

    def encode_address(address):
        """encode the address as a string describing the addres in hexadecimal

        Parameters
        ----------
        address : int 
            address of the device
            hold the 'Clear' button for several seconds to display it
            255 is the universal broadcat address (translates to 'FF')
        """
        
        if address != 255 and (address < 0 or address > 31)   : # wrong address provided
            raise AddressError(address)
        return self.hexify(address)
    
    def __init__(self, address, message, parameters):
        """construct a new CommandString instance

        Parameters
        ----------
        address : int
            address of the device
            ranges from 0 to 31, inclusive
        message : str
            string message, should be three characters long
        parameters : str
            parameters to the message
        """
        self.string="@"+self.encode_address(address)+message+parameters #make the first part of the message
        self.string=self.string.upper() #all characters must be uppercase
        self.string += self.sum(self.string) #add the checksum of the previous string contents
        self.string += "$0D" # end with the  CR character

class ReplyString(CommunicationString):
    """string reply from the device"""
    def __init__(self,reply, address=None):
        """construct a new ReplyString instance from the recieved reply string

        Parameters
        ----------
        reply : str
            the raw string recieved from the device
        address : int
        
        """
    
