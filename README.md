# yardly

Control home appliances with a [YardStick One](https://greatscottgadgets.com/yardstickone/).

Yardly offers a simple HTTP API for sending radio messages to wireless home appliances such
as ceiling fans and heated mattress pads.  It's meant as a backend for more sophisticated
home automation systems such as [Home Assistant](http://home-assistant.io) combined with
[Node RED](https://nodered.org/).  In a pinch, you can send it commands using `curl` or any
other web client.

I hope you find it useful.

# Usage

Run Yardly (see below).  Send it HTTP POST requests at port 8111.

## Docker Installation

Running Yardly in a container improves system security (a little bit) and
spares you from having to install Python 2.7 (needed by the rfcat library).

```
git clone (this repo)
cd yardly
git submodule update
docker-compose build
docker-compose up -d
curl http://myserver:8111/ping
```

## Standalone Installation

You can also run Yardly standalone but you'll first have to build and install
[rfcat](https://github.com/atlas0fd00m/rfcat).

```
git clone (this repo)
cd yardly
./yardly.py &
curl http://myserver:8111/ping
```

# Supported Devices

## Ceiling Fans (303.875 MHz)

Many fans sold in the US (and likely elsewhere) use generic transceivers that operate
at 303.875 MHz.  These fans are sold under a variety of brand names such as Emerson,
Hampton Bay, and Minka-Aire.

Each fan has a distinct code that is typically assigned using 4 or 5 DIP switches
in the remote control.

URL: "http://(hostname):8111/fan/(code)/(command)"

Code: A string of 4 or 5 zeroes and ones unique to the fan, e.g. `11011`

Commands:

- `off`

  Turns off the fan.

- `speed-1`, `speed-2`, `speed-3`, `speed-4`, `speed-5`, `speed-6`

  Sets the fan speed, 1 is the lowest, 6 is the highest.  Not all fan models
  support all 6 speeds.

  - For 3 speed fans, use `speed-1`, `speed-3`, and `speed-6`.
  - For 4 speed fans, use `speed-1`, `speed-3`, `speed-4`, and `speed-6`.

- `reverse`

  Reverses the fan direction.  Not all fan models support reversing by remote control;
  some instead have a physical switch on the motor casing to reverse direction.  You might
  need to grab a ladder.

- `toggle-downlight`, `toggle-uplight`

  Toggles the fan's downlight or uplight on or off.  This command only works with fans
  that have suitable light kits installed.  Unfortunately, there is no command for setting
  the light's state directly; it can only be toggled from its current state.

- `dim-downlight`, `dim-uplight`

  Toggles or dims the fan's downlight or uplight depending on how long the command is
  continuously repeated over the radio.  This command only works with fans that have
  suitable light kits and dimmable bulbs installed.  Unfortunately, there is no command
  for setting the light's intensity directly.
  
  If the command is repeated briefly (for about 200 to 600 ms) then the light's state is toggled.
  If the command is repeated for longer (for more than 700 ms) then the light's intensity will
  begin ramping up and down continuously for as long as the command repeats.

  Note: I haven't implemented an HTTP API for providing the command's repeat duration so these
  commands currently behave just like their toggling variants.  To be honest, they aren't
  all that useful.  I recommend installing smart bulbs in the light fixture instead of using the
  fan's built in dimmer.

Examples:

```
curl -X POST http://myserver:8111/fan/11011/speed-1
curl -X POST http://myserver:8111/fan/11011/off
```

## Sunbeam Therapeutic Heated Mattress Pad (418 MHz)

This heated mattress pad has six zones.  It's quite nice, just avoid washing it too often
because the electronics seem to deteriorate in the laundry and become less effective.
Refer to the product's manual for details.

Each mattress pad has a distinct 5-bit code.  I have no idea how to figure it out short
of using a logic analyzer (which I did) or trying every possibility.

URL: "http://(hostname):8111/mattress/(code)/(command)"

Code: A string of 5 zeroes and ones unique to the mattress pad, e.g. `11011`

Commands:

- `on`

  Turns off the mattress pad.

- `on/(lh),(lb),(lf),(rh),(rb),(rf),(stayOn),(preheat)`

  Turns on the mattress pad.  The settings are encoded as a comma-delimited sequence
  of values as follows:
  
  - `(lh)`: Left side head zone heat level, 0 (lowest) to 10 (highest).
  - `(lb)`: Left side body zone heat level, 0 (lowest) to 10 (highest).
  - `(lf)`: Left side feet zone heat level, 0 (lowest) to 10 (highest).
  - `(rh)`: Right side head zone heat level, 0 (lowest) to 10 (highest).
  - `(rb)`: Right side body zone heat level, 0 (lowest) to 10 (highest).
  - `(rf)`: Right side feet zone heat level, 0 (lowest) to 10 (highest).
  - `(stayOn)`: Optionally, specify "stayOn" to keep the mattress pad on indefinitely
  - `(preheat)`: Optionally, specify "preheat" to prewarm the mattress pad for 30 minutes
    before applying the provided heat levels

Examples:

```
curl -X POST http://myserver:8111/mattress/00000/on/1,1,2,1,2,3
curl -X POST http://myserver:8111/mattress/00000/on/1,1,2,1,2,3,stayOn
curl -X POST http://myserver:8111/mattress/00000/on/1,1,2,1,2,3,preheat
curl -X POST http://myserver:8111/mattress/00000/on/0,1,2,1,2,10,stayOn,preheat
curl -X POST http://myserver:8111/mattress/00000/off
```

# Troubleshooting

The YardStick One is a bit fussy to work with.  If you see the following messages,
here are some things you can try.

`Error in resetup():Exception('No Dongle Found.  Please insert a RFCAT dongle.',)`

- Make sure the Yardstick One is actually plugged in.
- Ensure that yardly has access to /dev/RFCAT1 such as by installing the recommended
  udev rules for rfcat and adding yardly's user to the "dialout" group.
- Try updating the Yardstick One firmware.

```
Error in resetup():USBError(110, u'Operation timed out')
Error in resetup():USBError(5, u'Input/Output Error')
```

- This sometimes happens after yardly is stopped and restarted.
- Try unplugging the YardStick One and plugging it back in again to reset it.

# Contributing

This project is currently somewhat barebones since I only needed to control a few
devices in my own home.  Feel free to send patches to improve the API, fix bugs,
add support for new devices, or make other improvements as you need.

