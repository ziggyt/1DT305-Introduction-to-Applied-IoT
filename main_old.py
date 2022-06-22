import machine
import network
import time
import urequests as requests
from machine import Pin, ADC
import ntptime

################################### ADAFRUIT IO SETUP ###################################

ADAFRUIT_IO_USERNAME = "<your adafruit IO username>"
ADAFRUIT_IO_KEY = "<your adafruit IO key>"

UV_INDEX_FEED = 'uv-index'

################################### SSID SETUP ##########################################

SSID = '<your ssid>'
WIFI_PASSWORD = '<your wifi password>'

################################### PIN SETUP ###########################################
uv_sensor_a = ADC(Pin(34))  # First UV sensor
uv_sensor_b = ADC(Pin(32))  # Second UV sensor

led_pin = Pin(2, Pin.OUT)  # Built-in LED

uv_sensor_a.atten(ADC.ATTN_11DB)  # 3.3v
uv_sensor_b.atten(ADC.ATTN_11DB)

################################### MISC SETUP ##########################################
RESOLUTION = 7
START_HOUR = 7
END_HOUR = 21
LED_BLINK_DELAY = 0.4
PRE_DEEPSLEEP_DELAY = 1


def setup_wifi():  # Init Wi-Fi and connect
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.connect(SSID, WIFI_PASSWORD)

    while not sta_if.isconnected():  # Blink while not connected
        led_alert()


def sync_time():  # Sync with time server
    ntptime.settime()


def get_current_hour():  # Get current hour and add 2 to adjust for Swedish time zone
    return time.localtime()[3] + 2


def adjust_analog_reading(value):  # Convert voltage range to 3.3v
    return (value * 3.3) / 1024


def send_value_to_adafruit_feed(value, feed_name: str):
    url = f'https://io.adafruit.com/api/v2/{ADAFRUIT_IO_USERNAME}/feeds/{feed_name}/data'
    body = {'value': str(value)}
    headers = {'X-AIO-Key': ADAFRUIT_IO_KEY, 'Content-Type': 'application/json'}

    try:
        requests.post(url, json=body, headers=headers)
        return True
    except Exception as e:
        print(e)


def led_alert():  # Blink led on and off
    led_pin.on()
    time.sleep(LED_BLINK_DELAY)
    led_pin.off()


################################### MAIN ##############################################

setup_wifi()  # Pre-req
sync_time()  # Pre-req

while True:

    if START_HOUR < get_current_hour() < END_HOUR:  # Only check UV sensors if time is within the specified range

        uv_analog_value_a = adjust_analog_reading(uv_sensor_a.read())  # Read sensors
        uv_analog_value_b = adjust_analog_reading(uv_sensor_b.read())

        uv_avg = (uv_analog_value_a + uv_analog_value_b) / 2  # Get average of both readings

        if 0 < uv_avg < 11:  # if the value is outside this range, something has gone wrong
            if send_value_to_adafruit_feed(uv_avg,
                                           UV_INDEX_FEED):  # Finally, send the collected sensor data to Adafruit IO

                led_alert()  # Blink once if successful
                time.sleep(PRE_DEEPSLEEP_DELAY)  # Sleep before deepsleep to avoid weird states
        else:
            for i in range(3):
                led_alert()  # This will only be reached if something has gone wrong with the readings. Flash LED 3 times and try again.
            continue

    machine.deepsleep(
        (RESOLUTION - PRE_DEEPSLEEP_DELAY) * 1000)  # To conserve energy we can use deepsleep (deepsleep is in ms)
