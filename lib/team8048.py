import time

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

# these have to all be imported in order for it not to crash on these packets
# https://github.com/adafruit/Adafruit_CircuitPython_BluefruitConnect/tree/master/adafruit_bluefruit_connect
from adafruit_bluefruit_connect.accelerometer_packet import AccelerometerPacket
from adafruit_bluefruit_connect.button_packet import ButtonPacket
from adafruit_bluefruit_connect.color_packet import ColorPacket
from adafruit_bluefruit_connect.gyro_packet import GyroPacket
from adafruit_bluefruit_connect.location_packet import LocationPacket
from adafruit_bluefruit_connect.magnetometer_packet import MagnetometerPacket
from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.quaternion_packet import QuaternionPacket

__all__ = [
    'run',
    'smartphone',
    'add_perpetual_command',
    'make_button',
]


class MockObject(object):

    def __init__(self, name):
        self.__name = name
        self.__attrs = {}

    def __getattr__(self, name):
        if name[0] != '_':
            print('mocking {}.{}'.format(self.__name, name))
            default_value = MockObject(name='{}.{}'.format(self.__name, name))
            return self.__attrs.get(name, default_value)
        else:
            return object.__getattr__(self, name)


class SmartPhone(object):

    def __init__(self):

        self.__uart = None
        self.__pending_plot_values = None

        self.button_1 = False
        self.button_2 = False
        self.button_3 = False
        self.button_4 = False

        self.button_up = False
        self.button_down = False
        self.button_left = False
        self.button_right = False

        self.acceleration = None
        self.magnetometer = None
        self.gyro = None
        self.quaternion = None
        self.color = None
        self.location = None

    def plot(self, *values):
        self.__pending_plot_values = values

    def _tick(self):
        if self.__uart:
            if self.__pending_plot_values:
                self.__uart.write('{}\n'.format(','.join([str(v) for v in self.__pending_plot_values])))
                self.__pending_plot_values = None
            if self.__uart.in_waiting:
                packet = Packet.from_stream(self.__uart)
                if isinstance(packet, ButtonPacket):
                    if packet.button == ButtonPacket.BUTTON_1:
                        self.button_1 = packet.pressed
                    elif packet.button == ButtonPacket.BUTTON_2:
                        self.button_2 = packet.pressed
                    elif packet.button == ButtonPacket.BUTTON_3:
                        self.button_3 = packet.pressed
                    elif packet.button == ButtonPacket.BUTTON_4:
                        self.button_4 = packet.pressed
                    elif packet.button == ButtonPacket.UP:
                        self.button_up = packet.pressed
                    elif packet.button == ButtonPacket.DOWN:
                        self.button_down = packet.pressed
                    elif packet.button == ButtonPacket.LEFT:
                        self.button_left = packet.pressed
                    elif packet.button == ButtonPacket.RIGHT:
                        self.button_right = packet.pressed
                if isinstance(packet, AccelerometerPacket):
                    self.acceleration = Axes(x=packet.x, y=packet.y, z=packet.z)
                if isinstance(packet, MagnetometerPacket):
                    self.magnetometer = Axes(x=packet.x, y=packet.y, z=packet.z)
                if isinstance(packet, GyroPacket):
                    self.gyro = Axes(x=packet.x, y=packet.y, z=packet.z)
                if isinstance(packet, QuaternionPacket):
                    self.quaternion = Quaternion(x=packet.x, y=packet.y, z=packet.z, w=packet.w)
                if isinstance(packet, ColorPacket):
                    self.color = packet.color
                if isinstance(packet, LocationPacket):
                    self.location = Location(latitude=packet.latitude, longitude=packet.longitude, altitude=packet.altitude)

    def _set_uart(self, uart):
        self.__uart = uart

    def _unset_uart(self):
        self.__uart = None


class Axes(object):
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z


class Location(object):
    def __init__(self, latitude, longitude, altitude):
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude


class Quaternion(object):
    def __init__(self, x, y, z, w):
        self.x = x
        self.y = y
        self.z = z
        self.w = w

class Button(object):

    _all_instances = []

    def __init__(self, value_getter):
        Button._all_instances.append(self)
        self.__value_getter = value_getter
        self.__value_last_tick = value_getter()
        self.__pressed_commands = []
        self.__released_commands = []
        self.__held_commands = []

    def __get_as_command(self, callback_or_command):
        if isinstance(callback_or_command, Command):
            return callback_or_command
        else:
            return Command(on_execute=callback_or_command)

    def when_pressed(self, callback_or_command):
        self.__pressed_commands.append(self.__get_as_command(callback_or_command))

    def when_released(self, callback_or_command):
        self.__released_commands.append(self.__get_as_command(callback_or_command))

    def while_held(self, callback_or_command):
        self.__held_commands.append(self.__get_as_command(callback_or_command))

    def __activate_commands_once(self, commands):
        for command in commands:
            command._activate_once()

    def _tick(self):
        new_value = self.__value_getter()
        if new_value != self.__value_last_tick:
            if new_value:
                self.__activate_commands_once(self.__pressed_commands)
            else:
                self.__activate_commands_once(self.__released_commands)
        elif new_value and new_value == self.__value_last_tick:
            self.__activate_commands_once(self.__held_commands)
        self.__value_last_tick = new_value


class Command(object):

    _all_instances = []
    _requirements_to_commands = {}

    # Mimics the FunctionalCommand of WPIlib
    # https://first.wpi.edu/FRC/roborio/release/docs/java/edu/wpi/first/wpilibj2/command/FunctionalCommand.html
    # https://docs.wpilib.org/en/stable/docs/software/commandbased/convenience-features.html
    def __init__(self, on_init=None, on_execute=None, on_end=None, is_finished=None, requirements=None):
        Command._all_instances.append(self)
        self.__on_init = on_init or (lambda: None)
        self.__on_execute = on_execute or (lambda: None)
        self.__on_end = on_end or (lambda: None)
        self.__is_finished = is_finished or (lambda: None)
        self.__requirements = requirements or []
        self.__active = False
        self.__once = False
        for requirement in self.__requirements:
            Command._requirements_to_commands[requirement] = Command._requirements_to_commands.get(requirement, [])
            Command._requirements_to_commands[requirement].append(self)

    def _is_active(self):
        return self.__active

    def _activate_once(self):
        self._activate(once=True)

    def _activate(self, once=False):
        if not self.__active:
            self.__active = True
            self.__once = once
            self.__on_init()

    def _deactivate(self, once=False):
        if self.__active:
            self.__active = False
            self.__on_end()

    # FIXME: this stops perpetual commands and won't let them restart
    def _find_conflicting_commands(self):
        for requirement in self.__requirements:
            for conflicting_command in Command._requirements_to_commands[requirement]:
                if conflicting_command._is_active():
                    conflicting_command._deactivate()

    def _tick(self):
        if self.__active:
            self.__on_execute()
            if self.__is_finished():
                self._deactivate()
            if self.__once:
                self._deactivate()


def _tick(expected_seconds_per_tick):
    start = time.monotonic()
    smartphone._tick()
    for button in Button._all_instances:
        button._tick()
    for command in Command._all_instances:
        command._tick()
    actual_seconds_for_tick = time.monotonic() - start
    seconds_remaining_to_sleep = expected_seconds_per_tick - actual_seconds_for_tick
    if seconds_remaining_to_sleep < 0:
        print("!!! exceeded time budget for a single tick by", int(seconds_remaining_to_sleep*-1000), "milliseconds")
    else:
        time.sleep(seconds_remaining_to_sleep)

def add_perpetual_command(callback):
    Command(on_execute=callback)._activate()

def run(cycles_per_second=30):
    ble = BLERadio()
    uart = UARTService()
    advertisement = ProvideServicesAdvertisement(uart)
    expected_seconds_per_tick = 1 / cycles_per_second
    while True:
        print("waiting for bluetooth connection")
        ble.start_advertising(advertisement)
        while not ble.connected:
            _tick(expected_seconds_per_tick=expected_seconds_per_tick)
        print("connected to bluetooth")
        smartphone._set_uart(uart=uart)
        while ble.connected:
            _tick(expected_seconds_per_tick=expected_seconds_per_tick)
        print("lost bluetooth connection")
        smartphone._unset_uart()

def make_button(value_getter):
    return Button(value_getter)

smartphone = SmartPhone()
mock_crickit = MockObject('crickit')
