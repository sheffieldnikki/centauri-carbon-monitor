#!/usr/bin/env python
"""
ccmonitor.py
Simple background monitor for Elegoo Centauri Carbon printers, and other SDCP 3D printers
see https://suchmememanyskill.github.io/OpenCentauri/software/api/
"""
# This work is licensed under CC0 Public Domain
# by Nikki Smith 2025, https://Climbers.net

import socket
import json
import asyncio
import sys
import os
import time

try:
    import websockets
except ImportError as err:
    sys.exit("Needs websockets. Try: 'pip install websockets'")


def request_status(uid, printer):
    """Returns message string to request status from printer"""
    # Cmd=0 for request printer status
    return ('{"Id": "'+uid+'", "Data": {"Cmd": 0, "Data": {}, '
      '"RequestID": "'+os.urandom(8).hex()+'", '
      '"MainboardID": "'+printer["MainboardID"]+'", "TimeStamp": '+str(int(time.time()))+', '
      '"From": 0}, "Topic": "sdcp/request/'+printer["MainboardID"]+'"}')

def display_status(prefix, printer, currentstatus, printstatus, suffix):
    """Display status change to console"""
    # TODO incomplete, CC sends some non-standard values
    # see https://github.com/suchmememanyskill/OpenCentauri/issues/23
    dict_currentstatus = {0: "Idle", 1: "Print", 2: "Upload", 3: "Calib", 4: "Test"}
    dict_printstatus = {0: "IDLE", 1: "HOMING", 2: "DROPPING", 3: "EXPOSING", 4: "LIFTING",
        5: "PAUSING", 6: "PAUSED", 7: "STOPPING", 8: "STOPPED", 9: "COMPLETE",
        10: "FILECHECK", 13: "PRINTING", 16: "HEATING"}
    status = dict_currentstatus.get(currentstatus, str(currentstatus))
    status += ':'+dict_printstatus.get(printstatus, str(printstatus))
    suffix += "\033[0m"
    print(f"{prefix}{printer['Name']: <24} @ {printer['MainboardIP']: <16} {status: <20} {suffix}")

def process_status(uid, printer, status):
    """Process received status JSON from printer"""
    currentstatus = int(status["CurrentStatus"][0])
    pinfo = status["PrintInfo"]
    printstatus = int(pinfo["Status"])
    tempofhotbed = round(float(status["TempOfHotbed"]))
    if float(pinfo["TotalTicks"]) > 0:
        jobpercent = round((float(pinfo["CurrentTicks"]) * 20) / float(pinfo["TotalTicks"])) * 5
    else:
        jobpercent = 0
    if len(oldstatus[uid]):
        pinfo = oldstatus[uid]["PrintInfo"]
        old_printstatus = int(pinfo["Status"])
        old_tempofhotbed = round(float(oldstatus[uid]["TempOfHotbed"]))
        if float(pinfo["TotalTicks"]) > 0:
            old_jobpercent = round((float(pinfo["CurrentTicks"]) * 20) /
                float(pinfo["TotalTicks"])) * 5
        else:
            old_jobpercent = 0
    else:
        old_printstatus = -1
        old_tempofhotbed = -1
        old_jobpercent = -1
    prefix = ""
    #
    # ADD EXTRA RULES HERE: check status, play sounds, run external commands, etc
    #
    if 5 <= printstatus <= 8:
        if old_printstatus < 5 or old_printstatus > 8:
            prefix = "\a" # beep!
        prefix += "\033[41m\033[37m" # pause/stop, in inverted red
    elif printstatus == 9:
        if old_printstatus != printstatus or (tempofhotbed <= 40 < old_tempofhotbed):
            prefix = "\a\033[42m\033[37m" # beep! complete (or bed cooled down), in inverted green
    elif currentstatus == 1:
        prefix = "\033[93m" # printing, in yellow

    # only display if status has changed
    # can't use CurrentLayer, not updated by CC firmware <= 1.1.29
    if printstatus not in [0, 9] and (printstatus != old_printstatus or
        jobpercent != old_jobpercent):
        display_status(prefix, printer, currentstatus, printstatus, str(jobpercent)+' %')
    elif printstatus in [0, 9] and (printstatus != old_printstatus or
        (tempofhotbed != old_tempofhotbed and tempofhotbed % 5 == 0)):
        suffix = 'bed '+str(tempofhotbed)+'\xb0C'
        display_status(prefix, printer, currentstatus, printstatus, suffix)
    oldstatus[uid] = status

async def monitor_status(uid, printer):
    """WebSocket connect to single printer, monitor for status changes"""
    url = "ws://"+printer["MainboardIP"]+":3030/websocket"
    async for websocket in websockets.connect(url):
        try:
            message = request_status(uid, printer)
            await websocket.send(message)
            async for response in websocket:
                response_json = json.loads(response)
                # ignore non-Status responses. eg, Acknowledgements
                if "Status" in response_json:
                    process_status(uid, printer, response_json["Status"])
        except json.JSONDecodeError:
            print(f"Response from {websocket.remote_address[0]} is invalid JSON")
        except websockets.ConnectionClosed:
            pass # restart connection?

async def main():
    """Monitor multiple printers"""
    print("\nRequesting printer status changes...\n")
    coroutines = [monitor_status(uid, printer) for uid, printer in printers.items()]
    try:
        await asyncio.gather(*coroutines)
    except asyncio.exceptions.CancelledError:
        pass

def scan_network():
    """Scan local network for SDCP printers with UDP broadcast"""
    # TODO periodically repeat to discover any new printers?
    broadcast_address = ('255.255.255.255', 3000)
    broadcast_message = "M99999"
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    print("Searching for SDCP printers on local network...\n")
    try:
        udp_socket.sendto(broadcast_message.encode(), broadcast_address)
        udp_socket.settimeout(3)
        while True:
            try:
                response, ipaddr = udp_socket.recvfrom(1024)
                response_json = json.loads(response.decode())
                if "Data" not in response_json or "Id" not in response_json:
                    print(f"Response from {ipaddr[0]} unrecognised as SDCP")
                    continue
                uid = response_json["Id"]
                printers[uid] = data = response_json["Data"]
                name = data.get('Name', '?')
                firmware = data.get('FirmwareVersion', '?')
                print(f"{name: <24} @ {ipaddr[0]: <16} firmware {firmware}")
                oldstatus[uid] = {}
            except json.JSONDecodeError:
                print(f"Response from {ipaddr[0]} is invalid JSON")
            except socket.timeout:
                break
    finally:
        udp_socket.close()
    if len(printers) == 0:
        sys.exit("No printers found")

# enable coloured text in Windows shell
if os.name == 'nt':
    os.system('color')
printers = {}
oldstatus = {}
scan_network()
asyncio.run(main())
