# You can use 'cpb' to control the Circuit Playground Bluefruit.
# https://circuitpython.readthedocs.io/projects/circuitplayground/en/latest/api.html
from adafruit_circuitplayground.bluefruit import cpb

# You can use 'crickit' to control the Crickit robotics board.
try:
    from adafruit_crickit import crickit
except Exception as err:
    print("WARNING:", err)
    print("WARNING: could not connect to the Crickit, booting into test mode")
    from team8048 import mock_crickit as crickit

# Use our custom team libraries to mimic the real FRC libraries for Buttons and Commands.
# You can use 'smartphone' to access the Bluefruit Connect app on iPhone or Android.
from team8048 import run
from team8048 import add_perpetual_command
from team8048 import make_button
from team8048 import smartphone

FWD = -1.0
REV = 0.7

OFF = (0, 0, 0)
RED = (200, 0, 0)
GREEN = (0, 200, 0)
BLUE = (0, 0, 200)
PURPLE = (120, 0, 160)
YELLOW = (100, 100, 0)
AQUA = (0, 100, 100)
COLOR_LIST = [PURPLE, YELLOW, GREEN, BLUE, AQUA]

NUMBER_OF_PIXELS = 10
PIXELS_PER_SECOND = 3
CYCLES_PER_SECOND = 30
PIXELS_TO_MOVE_PER_CYCLE = PIXELS_PER_SECOND / CYCLES_PER_SECOND

class my_robot:
    current_color_index = 0
    current_pixel = 0
    pixel_brightness = 0.02
    left_motor = crickit.dc_motor_1
    right_motor = crickit.dc_motor_2
    button_left = make_button(lambda: cpb.button_a)
    button_right = make_button(lambda: cpb.button_b)

brake_button = make_button(lambda: smartphone.button_1)
forward_button = make_button(lambda: smartphone.button_up)
reverse_button = make_button(lambda: smartphone.button_down)
left_button = make_button(lambda: smartphone.button_left)
right_button = make_button(lambda: smartphone.button_right)

def animate_light_around_circle():

    if my_robot.current_pixel >= NUMBER_OF_PIXELS:
        my_robot.current_pixel = 0
    elif my_robot.current_pixel <= 0:
        my_robot.current_pixel = NUMBER_OF_PIXELS - 1

    cpb.pixels.brightness = my_robot.pixel_brightness
    cpb.pixels.fill(OFF)
    cpb.pixels[int(my_robot.current_pixel)] = COLOR_LIST[my_robot.current_color_index]

    if cpb.switch:
        my_robot.current_pixel = my_robot.current_pixel - PIXELS_TO_MOVE_PER_CYCLE
    else:
        my_robot.current_pixel = my_robot.current_pixel + PIXELS_TO_MOVE_PER_CYCLE

def next_color():

    cpb.stop_tone()
    cpb.start_tone(400)
    my_robot.current_color_index = my_robot.current_color_index + 1
    if my_robot.current_color_index >= len(COLOR_LIST):
        my_robot.current_color_index = 0

def previous_color():

    cpb.stop_tone()
    cpb.start_tone(300)
    my_robot.current_color_index = my_robot.current_color_index - 1
    if my_robot.current_color_index < 0:
        my_robot.current_color_index = len(COLOR_LIST) - 1

def end_color_change():

    cpb.stop_tone()

def drive_forward():

    my_robot.pixel_brightness = 0.1
    cpb.pixels.fill(COLOR_LIST[my_robot.current_color_index])
    my_robot.left_motor.throttle = FWD
    my_robot.right_motor.throttle = FWD

def drive_backward():

    my_robot.pixel_brightness = 0.1
    cpb.pixels.fill(COLOR_LIST[my_robot.current_color_index])
    my_robot.left_motor.throttle = REV
    my_robot.right_motor.throttle = REV

def turn_right():

    color = COLOR_LIST[my_robot.current_color_index]
    cpb.pixels[0] = color
    cpb.pixels[1] = color
    cpb.pixels[2] = color
    cpb.pixels[3] = color
    cpb.pixels[4] = color
    my_robot.left_motor.throttle = FWD
    my_robot.right_motor.throttle = FWD * 0.5

def turn_left():

    color = COLOR_LIST[my_robot.current_color_index]
    cpb.pixels[5] = color
    cpb.pixels[6] = color
    cpb.pixels[7] = color
    cpb.pixels[8] = color
    cpb.pixels[9] = color
    my_robot.left_motor.throttle = FWD * 0.5
    my_robot.right_motor.throttle = FWD

def stop_driving():

    my_robot.pixel_brightness = 0.02
    cpb.pixels.fill(RED)
    my_robot.left_motor.throttle = 0.0
    my_robot.right_motor.throttle = 0.0

forward_button.while_held(drive_forward)
forward_button.when_released(stop_driving)

reverse_button.while_held(drive_backward)
reverse_button.when_released(stop_driving)

left_button.while_held(turn_left)
left_button.when_released(stop_driving)

right_button.while_held(turn_right)
right_button.when_released(stop_driving)

brake_button.while_held(stop_driving)

my_robot.button_left.when_pressed(previous_color)
my_robot.button_left.when_released(end_color_change)

my_robot.button_right.when_pressed(next_color)
my_robot.button_right.when_released(end_color_change)

add_perpetual_command(animate_light_around_circle)

run(CYCLES_PER_SECOND)
