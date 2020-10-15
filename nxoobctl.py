#!/usr/bin/env python3

import sys
import time
import json
import uuid
import asyncio
import ssl
import argparse
import os
import ipaddress
from argparse import RawDescriptionHelpFormatter

import websockets

def create_message(message, command_index=1):
    cmduuid = str(uuid.uuid4())
    data = {
        'jsonrpc': '2.0',
        'method': 'v1/notifyPluginLocalCommand',
        'params': {
            'clientAppGUID': cmduuid,
            'appGUID': message['appGUID'],
            'epoch': int(time.time()),
            'commandId': f'{cmduuid}|{command_index}',
            'commandSource': 'local',
            'moduleName': message['moduleName'], 
            'commands': [message['command']]
        }
    }
    return data

def validate_ip(ip):
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ipaddress.AddressValueError:
        return False

def create_set_config(arg):
    cmd = {
        'appGUID': 'bdc88ee7-f98b-46e9-9ea4-7fe3c69775a8',
        'moduleName': 'IPBased_NXODMDEMO2',
        'command': {
            'name': 'deviceConfig',
            'params': [{
                'name': 'deviceName',
                'value': 'SUNIX_EZM1150TS'
            },
            {
                'name': 'GMT',
                'value': 'UTC+0'
            },
            {
                'name': 'NTP',
                'value': ''
            }]
        }
    }
        
    pairs = args.arg.split(',')
    for pair in pairs: 
        key = ''
        value = ''
        try:
            key, value = pair.split('=', 1)
        except ValueError:
            print(f'set_config: invalid arg: "{arg}"', file=sys.stderr)
            sys.exit(1)
        if key in ('IPAddress', 'netMask', 'defaultGw', 'DNS'):
            if not validate_ip(value):
                print(f'set_config: invalid ip: "{key}={value}"', file=sys.stderr)
                sys.exit(1)
        elif key in ('IPMode'):
            if not value in ('STATIC', 'DHCP'):
                print(f'set_config: invalid mode: "{key}={value}"', file=sys.stderr)
                sys.exit(1)
        else:
            print(f'set_config: unknown parameter: "{key}={value}"', file=sys.stderr)
            sys.exit(1)
        
        new = {
            'name': key,
            'value': value
        }
        cmd['command']['params'].append(new)
        
    return cmd

MESSAGE_TYPES = {
    'get_config': {
        'appGUID': 'bdc88ee7-f98b-46e9-9ea4-7fe3c69775a8',
        'moduleName': 'IPBased_NXODMDEMO2',
        'command': {
            'name': 'getDeviceInfo'
        }
    },
    'set_config': {
        'factory': create_set_config,
    },
    'reboot': {
        'appGUID': 'bdc88ee7-f98b-46e9-9ea4-7fe3c69775a8',
        'moduleName': 'IPBased_NXODMDEMO2',
        'command': {
            'name': 'rebootHost',
            'params': [{
                'name': 'highPulseDurationReset',
                'value': '1000'
                }]
        }
    },
    'set_certificate': {
        'appGUID': 'bdmplugin',
        'moduleName': 'websocket',
        'command': {
            'name': 'UpdateClientCert',
            'params': [{
                'name': 'publicpem',
                'value': None # Insert public certificate here
            }]
        }
    }
}

async def send_message(uri, ssl_context, msg, debug=False):
    async with websockets.connect(uri, ssl=ssl_context) as ws:
        if debug:
            print(f'Sending message:\n{msg}')
        json_msg = json.dumps(msg)
        await ws.send(json_msg)
        json_ack = await asyncio.wait_for(ws.recv(), timeout=5.0)
        ack = json.loads(json_ack)
        if debug:
            print(f'Received ack:\n{ack}')
        if 'params' not in ack or 'commandState' not in ack['params'] or ack['params']['commandState'] != 'ACCEPTED':
            raise RuntimeError(f'Command not accepted by oob module. Received: {ack}')
        json_r = await asyncio.wait_for(ws.recv(), timeout=5.0)
        r = json.loads(json_r)
        if debug:
            print(f'Received message:\n{r}')
        return r

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='''oob module control

Available --commands:
    get_config
       Get target configuration
    reboot
       Reboot target system
    set_certificate CERTIFICATE
       Set public key required for authentication
       CERTIFICATE should point to certificate file
    set_config LIST
       Set target configuration
       LIST should be comma separated list of key=value pairs.
       Available keys:
          IPAddress
          netMask
          defaultGw
          DNS
          IPMode ( STATIC | DHCP )

Example:
    Read configuration:
    $ nxoobctl.py --uri wss://192.168.0.11:55688 -c get_config
    
    Set configuration, static ip 192.168.0.11
     $ nxoobctl.py --uri wss://192.168.0.11:55688 -c set_config IPAddress=192.168.0.11,IPMode=STATIC
''',
                                     epilog='''Return value:
0 for success, 1 for failure                                
''',
                                     formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('-c', '--command', required=True, help='Command to run on target')
    parser.add_argument('--uri', required=True, help='Target uri (wss://[ip]:[port]')
    parser.add_argument('arg', nargs='?', help="Arguments for selected command")
    parser.add_argument('-d', '--debug', action='store_true', help='Debug output')
    parser.add_argument('--key', help='Certificate private key')
    parser.add_argument('--cert', help='Certificate public key')
    args = parser.parse_args()
    
    if not args.command in MESSAGE_TYPES:
        print(f'--command "{args.command}" not supported', file=sys.stderr)
        sys.exit(1)
    
    # Test for commands requiring extra argument
    if args.command in ['set_certificate', 'set_config']:
        if not args.arg:
            print(f'--command "{args.command}" required additional arguments', file=sys.stderr)
            sys.exit(1)
    
    cmd = MESSAGE_TYPES[args.command]
    # Special handling for commands requiring argument
    if args.command == 'set_certificate':
        if not os.path.isfile(args.arg):
            print(f'"{args.arg}" not a file', file=sys.stderr)
            sys.exit(1)
        with open(args.arg, 'r') as f:
            cert = f.read()
        cmd['command']['params'][0]['value'] = cert
    elif args.command == 'set_config':
        cmd = MESSAGE_TYPES['set_config']['factory'](args.arg)
    msg = create_message(cmd)
    
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    # Add private and public keys if provided
    if args.key and args.cert:
        if not os.path.isfile(args.key):
            print(f'"{args.key}" not a file', file=sys.stderr)
            sys.exit(1)
        if not os.path.isfile(args.cert):
            print(f'"{args.cert}" not a file', file=sys.stderr)
            sys.exit(1)
        if args.debug:
            print(f'using authorization keys:\n  {args.key}\n  {args.cert}')
        ssl_context.load_cert_chain(args.cert, args.key)
            
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    r = asyncio.run(send_message(args.uri, ssl_context, msg, debug=args.debug))
    if 'params' in r and 'commandAcks' in r['params']:
        for data in r['params']['commandAcks']:
            if 'result' in data:
                for key, value in data['result'].items():
                    print(f'{key}: {value}')

    sys.exit(0)
