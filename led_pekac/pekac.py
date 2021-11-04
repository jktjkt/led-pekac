import asyncio
import asyncio_mqtt as am
import evdev
import smbus
import socket

wheel = None
button = None
mode_brightness = True
last_wheel_time = None
last_wheel_direction = None
brightness = 0
color = 5000

COLOR_MIN = 3000
COLOR_MAX = 6000
COLOR_SMALL_STEP = 50
BRIGHTNESS_MAX = 100
PWM_HZ = 25000
PWM_PERIOD = 1000000000 / PWM_HZ

REG_GLOBAL_CURRENT = 0x02
REG_CONFIG = 0x04
REG_PORT_CONF_4_5_6_7 = 0x09
REG_PORT4_ONLY = 0x24
NUMBER_OF_LEDS = 28
FIRST_LED_NUMBER = 4

class Max6956:
    digit_segments = [
            # dig1
            {
                'a': 24,
                'b': 25,
                'c': 19,
                'd': 20,
                'e': 21,
                'f': 22,
                'g': 23,
            },
            # dig2
            {
                'a': 27,
                'b': 28,
                'c': 15,
                'd': 17,
                'e': 18,
                'f': 26,
                'g': 16,
            },
            # dig3
            {
                'a': 6,
                'b': 30,
                'c': 10,
                'd': 14,
                'e': 11,
                'f': 7,
                'g': 29,
            },
            # dig4
            {
                'a': 31,
                'b': 4,
                'c': 8,
                'd': 9,
                'e': 13,
                'f': 5,
                'g': 12,
            },
        ]

    characters = {
        '0': 'abcdef',
        '1': 'bc',
        '2': 'abged',
        '3': 'abgcd',
        '4': 'fgbc',
        '5': 'afgcd',
        '6': 'afgedc',
        '7': 'abc',
        '8': 'abcdefg',
        '9': 'afbgcd',
        '-': 'g',
        'a': 'efabcg',
        'b': 'fgecd',
        'c': 'ged',
        'd': 'bcdeg',
        'e': 'afged',
        'f': 'afge',
        'h': 'fgec',
        'i': 'c',
        'j': 'bcde',
        'l': 'fed',
        'n': 'egc',
        'o': 'gced',
        'p': 'efabg',
        'r': 'eg',
        't': 'fged',
        'u': 'edc',
        'y': 'fgbe',
        ' ': '',

    }

    def __init__(self, i2c):
        self.i2c = i2c
        # All outputs are LEDs
        self.write_i2c(REG_PORT_CONF_4_5_6_7, 7 * [0x00])
        # Un-shutdown
        self.write_i2c(REG_CONFIG, [0x01])
        # Mid brightness
        self.write_i2c(REG_GLOBAL_CURRENT, [0x0a])
        self.show('    ')

    def show(self, text):
        if not isinstance(text, str) or len(text) != 4:
            raise RuntimeError('Four-character string is required')
        buf = NUMBER_OF_LEDS * [0]
        return self.set_segments(self.characters[char] for char in text.lower())

    def set_segments(self, digits):
        buf = NUMBER_OF_LEDS * [0]
        for digit, data in enumerate(digits):
            for segment in data:
                port = self.digit_segments[digit][segment]
                buf[port - FIRST_LED_NUMBER] = 1
        self.write_i2c(REG_PORT4_ONLY, buf)

    def write_i2c(self, register, data):
        # print(f'W: 0x{register:02x} {data}')
        self.i2c.write_block(register, data)


class I2CRegisters:
    def __init__(self, bus, device):
        self.bus = smbus.SMBus(bus)
        self.address = device

    def write_block(self, register, data):
        self.bus.write_i2c_block_data(self.address, register, data)

display = Max6956(I2CRegisters(1, 0x40))
# states = [
#     [['a'], [], [], []],
#     [[], ['a'], [], []],
#     [[], [], ['a'], []],
#     [[], [], [], ['a']],
#     [[], [], [], ['b']],
#     [[], [], [], ['c']],
#     [[], [], [], ['d']],
#     [[], [], ['d'], []],
#     [[], ['d'], [], []],
#     [['d'], [], [], []],
#     [['e'], [], [], []],
#     [['f'], [], [], []],
# ]
# i = 0
# while True:
#     display.set_segments(states[i % len(states)])
#     time.sleep(0.1)
#     i += 1
# raise 42


for device in (evdev.InputDevice(path) for path in evdev.list_devices()):
    capabilities = device.capabilities(absinfo=False)
    if capabilities == {0: [0, 2], 2: [0]}:
        wheel = device
        print(f'Wheel: {device.path} {device.name}')
    elif capabilities == {0: [0, 1], 1: [336]}:
        button = device
        print(f'Button: {device.path} {device.name}')


def to_pwm(brightness, color):
    relative_color = (color - COLOR_MIN) / (1.0 * (COLOR_MAX - COLOR_MIN))
    pwm_cool = int(PWM_PERIOD * brightness / BRIGHTNESS_MAX * relative_color)
    pwm_warm = int(PWM_PERIOD * brightness / BRIGHTNESS_MAX * (1 - relative_color))
    return pwm_cool, pwm_warm


def from_pwm(pwm_cool, pwm_warm):
    brightness = BRIGHTNESS_MAX * (pwm_cool + pwm_warm) / PWM_PERIOD
    if brightness > 0:
        color = (pwm_cool / PWM_PERIOD * COLOR_MAX + pwm_warm / PWM_PERIOD * COLOR_MIN) / brightness * BRIGHTNESS_MAX
    else:
        color = (COLOR_MAX - COLOR_MIN) / 2 + COLOR_MIN
    return round(brightness), round(color, -1)


def show_on_display():
    if mode_brightness:
        display.show(f'{brightness: >3} ')
    else:
        display.show(f'{int(color):4}')


def update_pwm(pwm_cool, pwm_warm):
    f_cool.seek(0)
    f_cool.write(str(pwm_cool))
    f_cool.flush()
    f_warm.seek(0)
    f_warm.write(str(pwm_warm))
    f_warm.flush()
    # print(f'{brightness}% {color}K')
    show_on_display()

async def handle_event(device):
    global mode_brightness, last_wheel_time, last_wheel_direction, brightness, color
    async for event in device.async_read_loop():
        e = evdev.util.categorize(event)
        if isinstance(e, evdev.events.KeyEvent):
            if e.scancode == 336 and e.keystate == e.key_down:
                last_wheel_time = None
                last_wheel_direction = None
                mode_brightness = not mode_brightness
                show_on_display()
        elif isinstance(e, evdev.events.RelEvent):
            delta = e.event.value
            if last_wheel_time is not None and last_wheel_direction == e.event.value:
                td = e.event.timestamp() - last_wheel_time
                rel = max(1.0, 1.0 / (66 * min(1.0, td)))
                delta *= int(rel)
            if mode_brightness:
                brightness += delta
                brightness = min(BRIGHTNESS_MAX, max(0, brightness))
            else:
                color += COLOR_SMALL_STEP * delta
                color = min(COLOR_MAX, max(COLOR_MIN, color))
            update_pwm(*to_pwm(brightness, color))
            last_wheel_time = e.event.timestamp()
            last_wheel_direction = e.event.value


f_cool = open('/sys/class/pwm/pwmchip0/pwm0/duty_cycle', 'r+')
f_warm = open('/sys/class/pwm/pwmchip0/pwm1/duty_cycle', 'r+')
brightness, color = from_pwm(int(f_cool.read()), int(f_warm.read()))
update_pwm(*to_pwm(brightness, color))


async def set_brighntess_from_mqtt(messages):
    async for message in messages:
        print(f'pekac: mqtt: brightness -> {message.payload}')
        brightness = int(message.payload)
        brightness = min(BRIGHTNESS_MAX, max(0, brightness))
        update_pwm(*to_pwm(brightness, color))


async def set_color_from_mqtt(messages):
    async for message in messages:
        print(f'pekac: mqtt: color -> {message.payload}')
        color = int(message.payload)
        color = min(COLOR_MAX, max(COLOR_MIN, color))
        update_pwm(*to_pwm(brightness, color))


async def cancel_tasks(tasks):
    for task in tasks:
        if task.done():
            continue
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


async def do_mqtt(server):
    my_hostname = socket.gethostname()
    topic_status = f'pekac/{my_hostname}/status'
    topic_set_brightness = f'pekac/{my_hostname}/set/brightness'
    topic_set_color = f'pekac/{my_hostname}/set/color'
    topic_brightness = f'pekac/{my_hostname}/brightness'
    topic_color = f'pekac/{my_hostname}/color'

    while True:
        try:
            async with AsyncExitStack() as stack:
                tasks = set()
                stack.push_async_callback(cancel_tasks, tasks)

                will = am.Will(topic=topic_status, payload='offline', retain=True)
                mqtt_client = am.Client(sys.argv[1], keepalive=3, client_id=f'pekac-{my_hostname}', will=will)
                await stack.enter_async_context(mqtt_client)
                print('pekac: connected to MQTT')

                msgs_brightness = await stack.enter_async_context(mqtt_client.filtered_messages(topic_set_brightness))
                tasks.add(asyncio.create_task(set_brighntess_from_mqtt(msgs_brightness), name='mqtt->brightness'))

                msgs_color = await stack.enter_async_context(mqtt_client.filtered_messages(topic_set_color))
                tasks.add(asyncio.create_task(set_color_from_mqtt(msgs_color), name='mqtt->color'))

                for topic in (topic_set_brightness, topic_set_color):
                    await mqtt_client.subscribe(topic)

                await mqtt_client.publish(topic_status, 'connecting...', retain=True)
                await asyncio.gather(*tasks)

        except am.MqttError as e:
            print(f'MQTT error: {e}')
        finally:
            await asyncio.sleep(1)

for device in wheel, button:
    asyncio.ensure_future(handle_event(device))

asyncio.ensure_future(do_mqtt)

loop = asyncio.get_event_loop()
loop.run_forever()
