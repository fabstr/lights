#!/usr/bin/python3

from astral import Astral
import datetime
from time import sleep
from pytradfri import Gateway
from pytradfri.api.libcoap_api import api_factory
import secrets

MIN_COLOR_TEMPERATURE=2000
MAX_COLOR_TEMPERATURE=5500
COLOR_TRANSITION_PERIOD=30

MIN_DIMMER=1
MAX_DIMMER=255
DIMMER_TRANSITION_PERIOD=30

# time to wake up, 2000K
MORNING_START = 7*60

# time for 2000K again
DAY_END = 22*60

# night start, only red light
NIGHT_START = 1*60



def getSunriseSunset(year, month, day):
    a = Astral()
    a.solar_depression = 'civil'
    city = a[secrets.CITY]
    sun = city.sun(date=datetime.date(year, month, day), local=True)
    sunrise = sun['sunrise'].hour * 60 + sun['sunrise'].minute
    sunset = sun['sunset'].hour * 60 + sun['sunset'].minute
    return (sunrise, sunset)

def getDimmer(time, sunrise, sunset):
    if time <= sunrise or time >= sunset:
        return MIN_DIMMER

    if time <= sunrise + DIMMER_TRANSITION_PERIOD:
        k = (MAX_DIMMER-MIN_DIMMER)/DIMMER_TRANSITION_PERIOD
        m = MIN_DIMMER
        x = time - sunrise
        return k*x + m

    if time >= sunset - DIMMER_TRANSITION_PERIOD:
        k = (MIN_DIMMER-MAX_DIMMER)/DIMMER_TRANSITION_PERIOD
        m = MAX_DIMMER
        x = DIMMER_TRANSITION_PERIOD - (sunset - time)
        return k*x + m

    return MAX_DIMMER


def getTemperature(time, sunrise, sunset):
    if time <= sunrise or time >= sunset:
        return MIN_COLOR_TEMPERATURE

    if time <= sunrise + COLOR_TRANSITION_PERIOD:
        k = (MAX_COLOR_TEMPERATURE-MIN_COLOR_TEMPERATURE)/COLOR_TRANSITION_PERIOD
        m = MIN_COLOR_TEMPERATURE
        x = time - sunrise
        return k*x + m

    if time >= sunset - COLOR_TRANSITION_PERIOD:
        k = (MIN_COLOR_TEMPERATURE-MAX_COLOR_TEMPERATURE)/COLOR_TRANSITION_PERIOD
        m = MAX_COLOR_TEMPERATURE
        x = COLOR_TRANSITION_PERIOD - (sunset - time)
        return k*x + m

    return MAX_COLOR_TEMPERATURE


def setTemperature(api, light, temperature):
    print(light.name, temperature, 'K set')
    api(light.light_control.set_kelvin_color(temperature))

def hintTemperature(api, light, temperature):
    # only set the temperature if the requested is warmer than the current
    if light.light_control.lights[0].kelvin_color > temperature:
        print(light.name, temperature, 'K hint')
        api(light.light_control.set_kelvin_color(temperature))


def hintDimmer(api, light, dimmer):
    # only actually set the dimmer if the requested value is < the current actual value
    if light.light_control.lights[0].dimmer > dimmer:
        print(light.name, round(100*dimmer/255), '% hint')
        dimmer = round(dimmer)
        if light.light_control.lights[0].state is True:
            # lamp is on
            api(light.light_control.set_dimmer(dimmer))

def setDimmer(api, light, dimmer):
    print(light.name, round(100*dimmer/255), '% set')
    dimmer = round(dimmer)
    if light.light_control.lights[0].state is True:
        # lamp is on
        api(light.light_control.set_dimmer(dimmer))

def forceDimmer(api, light, dimmer):
    print(light.name, round(100*dimmer/255), '% forced')
    dimmer = round(dimmer)
    api(light.light_control.set_dimmer(dimmer))

def setRGB(api, light, red, green, blue):
    print(light.name, red, green, blue, 'RGB')
    api(light.light_control.set_rgb_color(red, green, blue))

def main():
    api = api_factory(secrets.IP, secrets.KEY)

    devices_command = Gateway().get_devices()
    devices_commands = api(devices_command)
    devices = api(*devices_commands)
    lights = [dev for dev in devices if dev.has_light_control]

    now = datetime.datetime.now()
    time = now.hour*60 + now.minute

    (sunrise, sunset) = getSunriseSunset(now.year, now.month, now.day)
    temperature = getTemperature(time, sunrise, sunset)

    print("\ntime", time, NIGHT_START, MORNING_START)
    if time >= NIGHT_START and time < MORNING_START - 30:
        print("night")
        # red light at minimum
        for light in lights:
            if 'CWS' in light.device_info.model_number:
                setRGB(api, light, 255, 0, 0)
                setDimmer(api, light, 1)
            else:
                setTemperature(api, light, 2000)
                setDimmer(api, light, 1)
    elif time >= MORNING_START - 30 and time <= MORNING_START:
        dimmer = getDimmer(time, MORNING_START-30, 24*60)
        temperature = getTemperature(time, MORNING_START-30, 24*60)
        print("morning", dimmer, temperature)
        for light in lights:
            setTemperature(api, light, temperature)
            forceDimmer(api, light, dimmer)
    else:
        print("day")
        for light in lights:
            setTemperature(api, light, temperature)
            hintDimmer(api, light, 255) 

main()
