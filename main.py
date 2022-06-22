import network
from time import sleep
import urequests as requests
from machine import Pin, ADC, I2C, deepsleep
import ssd1306
import gc

################################### ADAFRUIT IO SETUP ###################################

ADAFRUIT_IO_USERNAME = "<your adafruit IO username>"
ADAFRUIT_IO_KEY = "<your adafruit IO key>"

UV_INDEX_FEED = 'uv-index'  # Add your own feed name here

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
LED_BLINK_DELAY = 0.4
PRE_DEEPSLEEP_DELAY = 1

i2c = I2C(sda=Pin(21), scl=Pin(22))
display = ssd1306.SSD1306_I2C(128, 64, i2c)


def setup_wifi():  # Init Wi-Fi and connect
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.connect(SSID, WIFI_PASSWORD)

    while not sta_if.isconnected():  # Blink while not connected
        led_alert()


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
        show_msg(e)


def led_alert():  # Blink led on and off
    led_pin.on()
    sleep(LED_BLINK_DELAY)
    led_pin.off()


def show_msg(data):
    display.fill(0)
    display.show()

    display.text(str(data), 0, 0, 1)
    display.show()


################################### MAIN ##############################################

setup_wifi()  # Pre-req

while True:
    gc.collect()  # To avoid ENOMEM errors
    gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())  # To avoid ENOMEM errors

    uv_analog_value_a = adjust_analog_reading(uv_sensor_a.read())  # Read sensors
    uv_analog_value_b = adjust_analog_reading(uv_sensor_b.read())

    uv_avg = (uv_analog_value_a + uv_analog_value_b) / 2  # Get average of both readings
    show_msg(f'UV Index: {uv_avg}')  # Show measured value on the OLED display

    if send_value_to_adafruit_feed(uv_avg, UV_INDEX_FEED):  # Finally, send the collected sensor data to Adafruit IO
        led_alert()  # Blink once if successful

    sleep(PRE_DEEPSLEEP_DELAY)  # Sleep before deepsleep to avoid weird states
    deepsleep((RESOLUTION - PRE_DEEPSLEEP_DELAY) * 1000)  # To conserve energy we can use deepsleep
