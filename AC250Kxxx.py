#!/usr/bin/python2

import serial as s

class AddressError(Exception):
    def __init__(self, address):
        self.address=address
    def __str__(self):
        return repr(self.address)

class CommunicationString:
    """general communication string container"""
    def hexify(number):
        """translate the number to an uppercase string representing it in hexadecimal"""
        #if number <0 : number*=-1 #TODO not sure if useful
        code=hex(address)[2:] #cut off the '0x' part
        if number < 16 : #if the number as hexadecimal is < 16 the hex string will have just one char
            code="0"+code# the hexadecimal address must have to characters
        return code.upper() #retrun a uppercase string
    def unhexify(hexstring):
        """translate an uppercase string representing a hexadecimal number
        the hexadecimal should _not_ start with 'x' or '0x' or anything similar
        """
        return int(hexstring, 16) #retrun the represented number in hexadecimal
    
    def sum(self,string=None):
        """sum([string]) -> sum

        calculate either the control cum of the provided string message
        or if no string was provided, calculate the control sum of the initial, address, message and parameters 
        
        return the sum as a string representing the sum in hexadecimal 
        """
        if string is None: #string not provided, construct it from the object info
            string=self.initial + self.address + self.message + self.parameters
        a=0
        for char in string:
            a+=ord(char)
        while a > 256:
            a-=256
        return self.hexify(a)

    def __str__(self):
        """string representation of this object -> raw communication string"""
        return self.string
    
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
    
