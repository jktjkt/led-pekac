import asyncio
import evdev

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


def update_pwm(pwm_cool, pwm_warm):
    f_cool.seek(0)
    f_cool.write(str(pwm_cool))
    f_cool.flush()
    f_warm.seek(0)
    f_warm.write(str(pwm_warm))
    f_warm.flush()
    print(f'{brightness}% {color}K')


async def handle_event(device):
    global mode_brightness, last_wheel_time, last_wheel_direction, brightness, color
    async for event in device.async_read_loop():
        e = evdev.util.categorize(event)
        if isinstance(e, evdev.events.KeyEvent):
            if e.scancode == 336 and e.keystate == e.key_down:
                last_wheel_time = None
                last_wheel_direction = None
                mode_brightness = not mode_brightness
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

for device in wheel, button:
    asyncio.ensure_future(handle_event(device))

loop = asyncio.get_event_loop()
loop.run_forever()
