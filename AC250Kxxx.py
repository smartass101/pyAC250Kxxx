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

def sum(string):
    """sum(string) -> sum_hexstring_repr

    Calculate the control sum of the provided uppercase string message as represented in hexadecimal.

    Parameters
    ----------
    string : str
        an uppercase string
        
    Returns
    -------
    sum_hexstring_repr : str
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


class AddressError(Exception):
    def __init__(self, address):
        self.address=address
    def __str__(self):
        return repr(self.address)

class CommunicationString:
    """general communication string container

    each communication string consists of several parts described in Attributes
    Attributes
    ----------
    initial : str
        the initial character
        determines the start of the packet
        '@' for a command packet
        '#' for a reply packet
    address : int
        address of the device
        ranges from 0 to 31, inclusive (32 possible addresses)
        address 255 is the broadcats address
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
    
