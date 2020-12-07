#!/usr/bin/env python3

import unittest
import subprocess
from subprocess import CalledProcessError

'''
All tests expect that certificate in CERT_PATH has already been installed
 $ nxoobctl.py --uri wss://192.168.0.130:55688 -c set_certificate cert.pub
 
Network environment for tests:
 OOB module:
  - Access to internet by gateway 192.168.0.254

'''

KEY_PATH =  './cert.key'
CERT_PATH = './cert.pub'
URI = 'wss://192.168.0.130:55688'
DEFAULT_CONFIG = {
    'deviceName': 'SUNIX_EZM1150TS',
    'IPMode': 'STATIC',
    'IPAddress': '192.168.0.130',
    'netmask': '255.255.255.0',
    'defaultGw': '192.168.0.254',
    'DNS': '8.8.8.8',
    'NTP': '0.europe.pool.ntp.org',
    'NTP2': '0.pool.ntp.org',
    'GMT': 'UTC+0',
    'fwVersion': '1.0.1-20201103-NXOOB',
    'GUID': '',
}

def nxoobctl(cmdlist, key=KEY_PATH, cert=CERT_PATH, uri=URI):
    args = ['./nxoobctl.py', '--uri', uri]
    if key and cert:
        args.extend(['--key', key, '--cert', cert])
    args.extend(['-c'])
    args.extend(cmdlist)
    r = subprocess.run(args, capture_output=True, text=True, check=True)
    return r.stdout

def config_to_dict(string):
    map = {}
    for pair in string.split('\n'):
        try:
            key, value = pair.split(': ', 1)
            map[key.strip()] = value.strip()
        except ValueError:
            map[pair.strip()] = ''
    return map

class test_get_config(unittest.TestCase):
    def setUp(self):
        self.cmd = ['get_config']
    def test_validate_default(self):
        r = nxoobctl(self.cmd)
        map = config_to_dict(r)
        for key, val in DEFAULT_CONFIG.items():
            self.assertTrue(key in map)
            self.assertTrue(map[key] == val)
            
    def test_unauthorized(self):
        with self.assertRaises(CalledProcessError):
            nxoobctl(self.cmd, key=None)
            
class test_reboot(unittest.TestCase):
    def setUp(self):
        self.cmd = ['reboot']
    def test_ok(self):
        nxoobctl(self.cmd)
    def test_unauthorized(self):
        with self.assertRaises(CalledProcessError):
            nxoobctl(self.cmd, key=None)

class test_set_config(unittest.TestCase):
    def setUp(self):
        self.cmd_set = ['set_config']
        self.cmd_get = ['get_config']
    def tearDown(self):
        cmd = self.cmd_set.copy()
        cmd.append(f'NTP={DEFAULT_CONFIG["NTP"]},NTP2={DEFAULT_CONFIG["NTP2"]},DNS={DEFAULT_CONFIG["DNS"]}')
        nxoobctl(cmd)
    def _test_var(self, key, value):
        cmd = self.cmd_set.copy()
        cmd.append(f'{key}={value}')
        nxoobctl(cmd)
        r = nxoobctl(self.cmd_get)
        map = config_to_dict(r)
        new_config = DEFAULT_CONFIG.copy()
        new_config[key] = value
        for key, val in new_config.items():
            self.assertTrue(key in map)
            self.assertTrue(map[key] == val)   
    def test_set_ntp(self):
        self._test_var('NTP', '3.pool.ntp.org')
    def test_set_ntp2(self):
        self._test_var('NTP2', '3.pool.ntp.org')
    def test_set_dns(self):
        self._test_var('DNS', '1.1.1.1')   
    def test_unauthorized(self):
        cmd = self.cmd_set.copy()
        cmd.append('DNS=1.2.3.4')
        with self.assertRaises(CalledProcessError):
            nxoobctl(cmd, key=None)

if __name__ == '__main__':
    unittest.main()
