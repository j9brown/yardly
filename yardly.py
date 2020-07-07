#!/usr/bin/env python2
import sys
import re
import rflib
import bottle

app = bottle.Bottle()
radio = rflib.RfCat()

# Converts an array of 0s and 1s to a string.
def bitsToBytes(bits):
    value = 0
    position = 128
    bytes = ""
    for bit in bits:
        if bit == "1":
            value += position
        position /= 2
        if position == 0:
            bytes += chr(value)
            value = 0
            position = 128
    if position != 128:
        bytes += chr(value)
        value = 0
        position = 128
    return bytes

# Sends a 13 bit ceiling fan command to the radio.
# Bits must be specified as a string of 1s and 0s.
#
#   bit  0-4: 5-bit fan address, prefix with 1 if code is only 4 bits
#   bit 7-12: 8-bit command
#
# Commands
#   00000100 : fan off
#   00010000 : fan speed 1 (low)
#   00010100 : fan speed 2
#   00100000 : fan speed 3 (medium)
#   00110000 : fan speed 4 (medium high)
#   01000100 : fan speed 5
#   01000000 : fan speed 6 (high)
#   00001000 : reverse
#   00000010 : adjust downlight; if dimmer bit is supported discard dimmer level,
#              otherwise keep dimmer level
#   00010010 : adjust uplight; if dimmer bit is supported discard dimmer level,
#              otherwise keep dimmer level
#   10000010 : adjust downlight; if dimmer bit is supported keep dimmer level,
#              otherwise this form cannot be used
#   10010010 : adjust uplight; if dimmer bit is supported keep dimmer level,
#              otherwise this form cannot be used
#
# Bits are sent over the radio from MSB to LSB.
#
# Frequency:    303.875 MhZ
# Mode:         ASK
# Rate:         1000 symbols per second / 3000 modulations per second
# Symbols:      0 -> "100", 1 -> "101"
# Guard:        36 modulations = 12 ms
# Code length:  13 symbols + guard = 75 modulations = 25 ms
#
# When adjusting downlight, repeating for duration < 600 ms toggles light
# off or on, holding for duration > 700 ms adjusts brightness.
#
# Need minimum of 2 repeats for any command to take effect.
# Use 400 ms (16 repeats) for reliability.
def sendFanBits(bits, repeats=16):
    # Apply modulation
    modulatedBits = ""
    for bit in bits:
        if bit == "0":
            modulatedBits += "100"
        else:
            modulatedBits += "101"

    # Add evenly spaced guards (multiples of 3 modulations)
    guard = "0" * 36
    modulatedBits = guard + (modulatedBits + guard) * repeats

    # Transmit
    radio.setFreq(303875000)
    radio.setMdmModulation(rflib.MOD_ASK_OOK)
    radio.setMdmDRate(3000)
    radio.setMdmSyncMode(0)
    radio.RFxmit(bitsToBytes(modulatedBits))

def encodeFanCommand(code, command):
    bits = ""
    if len(code) == 4:
        bits += "1"
    bits += code
    if command == "off":
        bits += "00000100"
    elif command == "speed-1":
        bits += "00010000"
    elif command == "speed-2":
        bits += "00010100"
    elif command == "speed-3":
        bits += "00100000"
    elif command == "speed-4":
        bits += "00110000"
    elif command == "speed-5":
        bits += "01000100"
    elif command == "speed-6":
        bits += "01000000"
    elif command == "reverse":
        bits += "00001000"
    elif command == "toggle-downlight":
        bits += "00000010"
    elif command == "toggle-uplight":
        bits += "00010010"
    elif command == "dim-downlight":
        bits += "10000010"
    elif command == "dim-uplight":
        bits += "10010010"
    else:
        return None
    return bits

# Sends a 25 bit mattress pad command to the radio.
# Bits must be specified as a string of 1s and 0s.
#
#   bit   0-5 : checksum (count of 1 bits)
#   bit   6-8 : 3-bit zone
#   bit  9-13 : 5-bit code
#   bit 14-16 : zeroes
#   bit 17-20 : heat level
#   bit    21 : zero
#   bit    22 : stay-on
#   bit    23 : preheat
#   bit    24 : on
#
# Zones
#   000 : right head
#   001 : right body
#   010 : right feet
#   100 : left head
#   101 : left body
#   110 : left feet
#
# Code begins with a mark followed by a break then the command,
# another break then the command, etc.
#
# Bits are sent over the radio from LSB to MSB.
#
# Frequency:    418 MhZ
# Mode:         ASK
# Rate:         533 symbols per second / 1600 modulations per second
# Symbols:      0 -> "100", 1 -> "101"
# Start:        "111111000000"
def sendMattressBits(bits, repeats=3):
    # Apply modulation
    modulatedBits = ""
    for bit in bits[::-1]:
        if bit == "0":
            modulatedBits += "100"
        else:
            modulatedBits += "101"

    # Add marks, breaks, and repetitions
    modulatedBits = ("111111000000" + modulatedBits) * repeats

    # Transmit
    radio.setFreq(418000000)
    radio.setMdmModulation(rflib.MOD_ASK_OOK)
    radio.setMdmDRate(1600)
    radio.setMdmSyncMode(0)
    print modulatedBits
    radio.RFxmit(bitsToBytes(modulatedBits))

def encodeMattressCommand(code, on, zone, level, stayOn, preheat):
    bits = zone
    bits += code
    bits += "000"
    bits += format(level, "04b")
    bits += "0"
    bits += "1" if stayOn else "0"
    bits += "1" if preheat else "0"
    bits += "1" if on else "0"
    checksum = format(bits.count("1"), "06b")
    return checksum + bits

# Replies with pong.
@app.get("/ping")
def handlePingRequest():
    return "pong"

# Sends a fan command.
#
#   code: fan code (string of 4 or 5 bits)
#   command: "off", "speed-1".."speed-6", "reverse",
#            "toggle-uplight", "toggle-downlight",
#            "dim-uplight", "dim-downlight
@app.post("/fan/<code:re:[0-1]{4,5}>/<command>")
def handleFanRequest(code, command):
    bits = encodeFanCommand(code, command)
    if bits == None:
        bottle.abort(400, "Invalid fan command")
    sendFanBits(bits)
    return "sent fan bits " + bits

# Sends raw bits to a fan.
#
#   bits: string of 0s and 1s
#   repeat: number of repetitions to send
@app.post("/fanBits/<bits:re:[0-1]+>/<repeats:int>")
def handleFanBitsRequest(bits, repeats):
    sendFanBits(bits, repeats)
    return "sent fan bits " + bits

# Sends a mattress pad off command.
#
#   code: mattress code (string of 5 bits)
@app.post("/mattress/<code:re:[0-1]{5}>/off")
def handleMattressOffRequest(code):
    sendMattressBits(encodeMattressCommand(code, False, "100", 0, False, False))
    sendMattressBits(encodeMattressCommand(code, False, "000", 0, False, False))
    return "sent mattress off command"

# Sends a mattress pad on command.
#
#   code: mattress code (string of 5 bits)
#   command: comma-delimited sequence of heat levels from 0-1 in order
#            left head, left body, left feet, right head, right body, right feet
#            followed by optional comma-delimited flags "stayOn" or "preheat"
#            in that order
@app.post("/mattress/<code:re:[0-1]{5}>/on/<command>")
def handleMattressOnRequest(code, command):
    m = re.match(r'^(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)(,stayOn)?(,preheat)?$', command)
    if m == None:
        bottle.abort(400, "Invalid mattress command")
    heat = [
      int(m.group(1)),
      int(m.group(2)),
      int(m.group(3)),
      int(m.group(4)),
      int(m.group(5)),
      int(m.group(6))
    ]
    stayOn = m.group(7) != None
    preheat = m.group(8) != None
    sendMattressBits(encodeMattressCommand(code, True, "100", heat[0], stayOn, preheat))
    sendMattressBits(encodeMattressCommand(code, True, "101", heat[1], stayOn, preheat))
    sendMattressBits(encodeMattressCommand(code, True, "110", heat[2], stayOn, preheat))
    sendMattressBits(encodeMattressCommand(code, True, "000", heat[3], stayOn, preheat))
    sendMattressBits(encodeMattressCommand(code, True, "001", heat[4], stayOn, preheat))
    sendMattressBits(encodeMattressCommand(code, True, "010", heat[5], stayOn, preheat))
    return "sent mattress on command"

# Sends raw bits to a mattress pad.
#
#   bits: string of 0s and 1s
#   repeat: number of repetitions to send
@app.post("/mattressBits/<bits:re:[0-1]+>/<repeats:int>")
def handleMattressBitsRequest(bits, repeats):
    sendMattressBits(bits, repeats)
    return "sent mattress bits " + bits

bottle.run(app, host="0.0.0.0", port=8111)
