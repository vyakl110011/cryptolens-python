# -*- coding: utf-8 -*-
"""
Created on Wed Jan 23 09:47:26 2019

@author: Artem Los
"""
import xml.etree.ElementTree
import json
import base64
import datetime
import copy
import time

from licensing.internal import HelperMethods

class ActivatedMachine:
    def __init__(self, IP, Mid, Time):
        self.IP = IP
        self.Mid = Mid
        
        # TODO: check if time is int, and convert to datetime in this case.
        self.Time = Time

class LicenseKey:
    
    def __init__(self, ProductId, ID, Key, Created, Expires, Period, F1, F2,\
                 F3, F4, F5, F6, F7, F8, Notes, Block, GlobalId, Customer, \
                 ActivatedMachines, TrialActivation, MaxNoOfMachines, \
                 AllowedMachines, DataObjects, SignDate, RawResponse):
        
        self.product_id = ProductId
        self.id = ID
        self.key = Key
        self.created = Created
        self.expires = Expires
        self.period = Period
        self.f1 = F1
        self.f2 = F2
        self.f3 = F3
        self.f4 = F4
        self.f5 = F5
        self.f6 = F6
        self.f7 = F7
        self.f8 = F8
        self.notes = Notes
        self.block = Block
        self.global_id = GlobalId
        self.customer = Customer
        self.activated_machines = ActivatedMachines
        self.trial_activation = TrialActivation
        self.max_no_of_machines = MaxNoOfMachines
        self.allowed_machines = AllowedMachines
        self.data_objects = DataObjects
        self.sign_date = SignDate
        self.raw_response = RawResponse
        
    @staticmethod
    def from_response(response):
        
        if response.result == "1":
            raise ValueError("The response did not contain any license key object since it was unsuccessful. Message '{0}'.".format(response.message))
        
        obj = json.loads(base64.b64decode(response.license_key).decode('utf-8'))
        
        return LicenseKey(obj["ProductId"], obj["ID"], obj["Key"], datetime.datetime.fromtimestamp(obj["Created"]),\
                          datetime.datetime.fromtimestamp(obj["Expires"]), obj["Period"], obj["F1"], obj["F2"], \
                          obj["F3"], obj["F4"],obj["F5"],obj["F6"], obj["F7"], \
                          obj["F8"], obj["Notes"], obj["Block"], obj["GlobalId"],\
                          obj["Customer"], LicenseKey.__load_activated_machines(obj["ActivatedMachines"]), obj["TrialActivation"], \
                          obj["MaxNoOfMachines"], obj["AllowedMachines"], obj["DataObjects"], \
                          datetime.datetime.fromtimestamp(obj["SignDate"]), response)
        
    def save_as_string(self):
        """
        Save the license as a string that can later be read by load_from_string.
        """
        res = copy.copy(self.raw_response.__dict__)
        res["licenseKey"] = res["license_key"]
        res.pop("license_key", None)
        return json.dumps(res)
    
    @staticmethod
    def load_from_string(rsa_pub_key, string, signature_expiration_interval = -1):
        """
        Loads a license from a string generated by save_as_string.
        Note: if an error occurs, None will be returned. An error can occur
        if the license string has been tampered with or if the public key is
        incorrectly formatted.
        
        :param signature_expiration_interval: If the license key was signed,
        this method will check so that no more than "signatureExpirationInterval" 
        days have passed since the last activation.
        """
        
        response = Response("","","","")
        
        try:
            response = Response.from_string(string)
        except Exception as ex:
            return None
        
        if response.result == "1":
            return None
        else:
            try:
                pubKey = RSAPublicKey.from_string(rsa_pub_key)
                if HelperMethods.verify_signature(response, pubKey):
                    
                    licenseKey = LicenseKey.from_response(response)
                    
                    if signature_expiration_interval > 0 and \
                    (licenseKey.sign_date + datetime.timedelta(days=1*signature_expiration_interval) < datetime.datetime.utcnow()):
                        return None
                    
                    return licenseKey
                else:
                    return None
            except Exception:
                return None
      
    @staticmethod
    def __load_activated_machines(obj):
        
        if obj == None:
            return None
        
        arr = []
        
        for item in obj:
            arr.append(ActivatedMachine(**item))
        
        return arr

class Response:
    
    def __init__(self, license_key, signature, result, message):
        self.license_key = license_key
        self.signature = signature
        self.result = result
        self.message = message
        
    @staticmethod
    def from_string(responseString):        
        obj = json.loads(responseString)
        
        licenseKey = ""
        signature = ""
        result = 0
        message = ""
        
        if "licenseKey" in obj:
            licenseKey = obj["licenseKey"]
            
        if "signature" in obj:
            signature = obj["signature"]
        
        if "message" in obj:
            message = obj["message"]
            
        if "result" in obj:
            result = obj["result"]
        else:
            result = 1
        
        return Response(licenseKey, signature, result, message)
        
class RSAPublicKey:
    
    def __init__(self, modulus, exponent):
        self.modulus = modulus
        self.exponent = exponent
        
    @staticmethod
    def from_string(rsaPubKeyString):
        """
        The rsaPubKeyString can be found at https://app.cryptolens.io/User/Security.
        It should be of the following format:
            <RSAKeyValue><Modulus>...</Modulus><Exponent>AQAB</Exponent></RSAKeyValue>
        """
        rsaKey = xml.etree.ElementTree.fromstring(rsaPubKeyString)
        return RSAPublicKey(rsaKey.find('Modulus').text, rsaKey.find('Exponent').text)
        