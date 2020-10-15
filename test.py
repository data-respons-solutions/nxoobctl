#!/usr/bin/env python3

import unittest
import subprocess
from subprocess import CalledProcessError

KEY_PATH =  './cert.key'
CERT_PATH = './cert.pub'
URI = 'wss://192.168.0.130:55688'
DEFAULT_CONFIG = {
    'deviceName': 'SUNIX_EZM1150TS',
    'IPMode': 'STATIC',
    'IPAddress': '192.168.0.130',
    'netmask': '255.255.255.0',
    'defaultGw': '192.168.0.254',
    'DNS': '0.0.0.0',
    'NTP': '',
    'GMT': 'UTC+0',
    'fwVersion': '1.0.0-20201014-NXOOB',
    'GUID': '',
}

'''
All tests expect that certificate in CERT_PATH has already been installed to module
Note:
  FW EZM1150TS_MT0_V1_0_20201014_SDK_PRODUCT_OPMI_NXOOB.rom:
    Module did not accept connections after intalling certificate
'''

def nxoobctl(cmdlist, key=KEY_PATH, cert=CERT_PATH, uri=URI):
    args = ['./nxoobctl.py', '--uri', uri]
    if key and cert:
        args.extend(['--key', key, '--cert', cert])
    args.extend(['-c'])
    args.extend(cmdlist)
    r = subprocess.run(args, capture_output=True, text=True, check=True)
    return r.stdout

class test_get_config(unittest.TestCase):
    def setUp(self):
        self.cmd = 'get_config'
    def test_validate_default(self):
        r = nxoobctl([self.cmd])
        map = {}
        for pair in r.split('\n'):
            try:
                key, value = pair.split(': ', 1)
                map[key.strip()] = value.strip()
            except ValueError:
                map[pair.strip()] = ''

        for key, val in DEFAULT_CONFIG.items():
            self.assertTrue(key in map)
            self.assertTrue(map[key] == val)
            
    def test_unauthorized(self):
        with self.assertRaises(CalledProcessError):
            nxoobctl([self.cmd], key=None)
            
class test_reboot(unittest.TestCase):
    def setUp(self):
        self.cmd = 'reboot'
    def test_ok(self):
        nxoobctl([self.cmd])
    def test_unauthorized(self):
        with self.assertRaises(CalledProcessError):
            nxoobctl([self.cmd], key=None)
        
if __name__ == '__main__':
    unittest.main()