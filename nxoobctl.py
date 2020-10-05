#!/usr/bin/env python3

import sys
import time
import json
import uuid
import asyncio
import ssl
import argparse
import os
from argparse import RawDescriptionHelpFormatter

import websockets

COMMANDS = {
    'get_config': {
        'name': 'getDeviceInfo',
    },
    'reboot': {
        'name': 'rebootHost',
        'params': [{
            'name': 'highPulseDurationReset',
            'value': '1000'
        }]
    }
}

def create_message(command, command_index=1):
    cmduuid = str(uuid.uuid4())
    data = {
        'jsonrpc': '2.0',
        'method': 'v1/notifyPluginLocalCommand',
        'params': {
            'clientAppGUID': cmduuid,
            'appGUID': 'bdc88ee7-f98b-46e9-9ea4-7fe3c69775a8',
            'epoch': int(time.time()),
            'commandId': f'{cmduuid}|{command_index}',
            'commandSource': 'local',
            'moduleName': 'IPBased_NXODMDEMO2',            
            'commands': [command]
        }
    }
    return data

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
    get_config       Get target configuration
    reboot           Reboot target system
    
Example:
    Read configuration:
    $ nxoobctl.py --uri wss://192.168.0.11:55688 -c get_config
''',
                                     epilog='''Return value:
0 for success, 1 for failure                                
''',
                                     formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('-c', '--command', required=True, help='Command to run on target')
    parser.add_argument('--uri', required=True, help='Target uri (wss://[ip]:[port]')
    parser.add_argument('arg', nargs='?', help="Arguments for selected command")
    parser.add_argument('-d', '--debug', action='store_true', help='Debug output')
    args = parser.parse_args()
    
    if not args.command in COMMANDS:
        print(f'--command "{args.command}" not supported', file=sys.stderr)
        sys.exit(1)
    
    msg = create_message(COMMANDS[args.command])
    json_msg = json.dumps(msg)
    
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    r = asyncio.run(send_message(args.uri, ssl_context, msg, debug=args.debug))
    if 'params' in r and 'commandAcks' in r['params']:
        for data in r['params']['commandAcks']:
            if 'result' in data:
                for key, value in data['result'].items():
                    print(f'{key}: {value}')

    sys.exit(0)
