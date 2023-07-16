import esp32
import time
import network, time
import math
import urequests
import machine
import ubinascii
from machine import Pin, UART, freq, WDT

freq(80000000) # Underclock to 80MHz to save power, keep things cooler, why not

UPDATE_TIME_INTERVAL = 5000  # in ms 
last_update = time.ticks_ms() 

UART_NUM = 2

WIFI_SSID = 'redacted'
WIFI_PASS = 'redacted'
THINGSPEAK_WRITE_API_KEY = 'redacted'

# Initialize network
sta_if=network.WLAN(network.STA_IF)
sta_if.active(True)
if not sta_if.isconnected():
    print('connecting to network...')
    sta_if.connect(WIFI_SSID, WIFI_PASS)
    while not sta_if.isconnected():
        pass
print('network config:', sta_if.ifconfig())

# Initialize APC sensor over UART
uart = UART(UART_NUM, 9600)
uart.init(9600, bits=8, parity=None, stop=1, timeout=1000, timeout_char=10)
print(uart)

APC_CMD_READ = ubinascii.unhexlify('424DE200000171')
APC_CMD_SENSORINFO = ubinascii.unhexlify('424DE900000178')
HTTP_HEADERS = {'Content-Type': 'application/json'} 

def take_measurement():
    print('Taking Measurement...')
    uart.write(APC_CMD_READ)
    val = uart.read()

    pm1  = int.from_bytes(val[4:6], "big")
    pm2  = int.from_bytes(val[6:8], "big")
    pm10 = int.from_bytes(val[8:10], "big")
    tvoc = int.from_bytes(val[28:30], "big")
    eco2 = int.from_bytes(val[30:32], "big")
    temp = int.from_bytes(val[34:36], "big") / 10.0
    hum  = int.from_bytes(val[36:38], "big") / 10.0
    aqi = val[58]

    temp_f = temp * 9 / 5 + 32

    return {'field1': temp_f, 'field2': hum, 'field3': pm1, 'field4': pm2, 'field5': pm10, 'field6': tvoc, 'field7': eco2, 'field8': aqi}

time.sleep(2) # Initialize
wdt = WDT(timeout=120000) # 2 Minute watchdog
wdt.feed()

while True:
    try:
        if time.ticks_ms() - last_update >= UPDATE_TIME_INTERVAL:
            data = take_measurement()
            request = urequests.post( 'http://api.thingspeak.com/update?api_key=' + THINGSPEAK_WRITE_API_KEY, json = data, headers = HTTP_HEADERS)
            request.close()
            print(data)
            last_update = time.ticks_ms()
    except Exception as e:
        print("Could not get and send update")

    wdt.feed()
