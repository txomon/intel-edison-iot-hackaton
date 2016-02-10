from __future__ import print_function
import argparse
try:
    import simplejson as json
except ImportError:
    import json
import logging
import os
import requests
import time

logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s:IntelBoard:%(levelname)s:%(message)s'
)
logger = logging.getLogger()

class Component(object):
    connector = None
    pin = None
    keyword = ''
    actuator = None

    def set_up(self, component):
        assert(self.keyword == component['type'])
        if not self.register_location(component.get('pin', '')):
            logger.error('Registering location went wrong')
            return False
        if not self.register_custom(component):
            logger.error('Registering custom properties went wrong')
            return False
        self.actuator = self.get_actuator()
        self.initialize()
        return True

    def register_custom(self, component):
        return True

    def initialize(self):
        pass
    
    def register_location(self, location):
        location = location.upper()
        if self.connector == 'analogical':
            if not location in ['A0', 'A1', 'A2', 'A3']:
                logger.error('%s should be placed in analogical A[0-3] connectors')
                return False
            self.pin = int(location[1])
        elif self.connector == 'digital':
            if not location in ['D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8']:
                logger.error('%s should be placed in digital D[2-8] connectors')
                return False
            self.pin = int(location[1])
        elif self.connector == 'UART':
            if not location in ['UART']:
                logger.error('%s should be placed in UART connector')
                return False
            self.pin = 'UART'
        elif self.connector == 'I2C':
            if not location in ['I2C']:
                logger.error('%s should be placed in I2C connector')
                return False
            self.pin = 'I2C'
        return True

    def set_value(self, new_value):
        pass

    def get_value(self):
        pass

    value = property(get_value, set_value)

    __nonzero__ = lambda s: s.value

    __repr__ = lambda s: s.value.__repr__()
    __str__ = lambda s: s.value.__str__()
    __lt__ = lambda s, o: s.value.__lt__(o)
    __le__ = lambda s, o: s.value.__le__(o)
    __eq__ = lambda s, o: s.value.__eq__(o)
    __ne__ = lambda s, o: s.value.__ne__(o)
    __gt__ = lambda s, o: s.value.__gt__(o)
    __ge__ = lambda s, o: s.value.__ge__(o)
    __cmp__ = lambda s, o: s.value.__cmp__(o)
    __unicode__ = lambda s: s.value.__unicode__()

    @classmethod
    def generate_help(cls):
        print("Module %s doesn't have documentation"% cls.__name__)
        print("But, the type is '%s' and the pin has to be '%s'" % (cls.keyword, cls.connector))

try:
    import pyupm_grove

    class GroveLed(Component):
        keyword = 'led'
        connector = 'digital'

        def __init__(self):
            super(GroveLed, self).__init__()
            self._value = False

        def get_actuator(self):
            return pyupm_grove.GroveLed(self.pin)

        def set_value(self, new_value):
            logger.debug('Changing value to %r', new_value)
            if new_value:
                self._value = True
                self.actuator.on()
            else:
                self._value = False
                self.actuator.off()

        def get_value(self):
            logger.debug('Returning led state %r', self._value)
            return self._value

        value = property(get_value, set_value)

    class GroveButton(Component):
        keyword = 'button'
        connector = 'digital'

        def get_actuator(self):
            return pyupm_grove.GroveButton(self.pin)

        def get_value(self):
            return self.actuator.value()

        value = property(get_value)

    class GroveLight(Component):
        keyword = 'light_sensor'
        connector = 'analogical'

        def get_actuator(self):
            return pyupm_grove.GroveLight(self.pin)

        def get_value(self):
            return self.actuator.value()

        value = property(get_value)

    class GroveRelay(Component):
        keyword = 'relay'
        connector = 'digital'

        def get_actuator(self):
            return pyupm_grove.GroveLight(self.pin)

        def get_value(self):
            return self.actuator.isOn()

        def set_value(self, value):
            if value:
                self.actuator.on()
            else:
                self.actuator.off()

        value = property(get_value, set_value)


    class GroveRotary(Component):
        keyword = 'rotary'
        connector = 'analogical'

        def get_actuator(self):
            return pyupm_grove.GroveRotary(self.pin)

        def get_value(self):
            return self.actuator.abs_deg()

        value = property(get_value)


    class GroveSlide(Component):
        keyword = 'slide'
        connector = 'analogical'

        def __init__(self):
            super(GroveSlide, self).__init__()
            self._ref = 5

        def get_actuator(self):
            return pyupm_grove.GroveSlide(self.pin, self.ref)

        def get_value(self):
            return self.actuator.value()

        value = property(get_value)

        ref = property(lambda s: s._ref)

        def register_custom(self, component):
            self._ref = component.get('ref', 5)


    class GroveTemp(Component):
        keyword = 'temperature'
        connector = 'analogical'

        def get_actuator(self):
            return pyupm_grove.GroveTemp(self.pin)

        def get_value(self):
            return self.actuator.value()

        value = property(get_value)

except ImportError:
    logger.warn('pyupm_grove library is missing in the python module path')
    logger.warn('"led", "button", "light_sensor", "relay", "rotary", "slide"'
            ' and "temperature" types will not be available')

try: 
    import pyupm_mic

    class Microphone(Component):
        keyword = 'microphone'
        connector = 'analogical'
        _sample_rate = 2
        threshold = 160
        samples = 64

        def __init__(self):
            super(Microphone, self).__init__()
            self.ctx = None

        def get_actuator(self):
            return pyupm_mic.Microphone(self.pin)

        def get_value(self):
            sample_buffer = pyupm_mic.uint16Array(self.samples)
            s_num = self.actuator.getSampledWindow(
                    self._sample_rate,
                    self.samples,
                    sample_buffer
            )
            if s_num:
                db = self.actuator.findThreshold(
                        self.ctx,
                        self.threshold,
                        sample_buffer,
                        self.samples
                )
                return db

            logger.info('No actual data from microphone')
            return False

        value = property(get_value)

        def register_custom(self, component):
            self.threshold = component.get('threshold', self.threshold)
            self._sample_rate = component.get('sample_rate', self._sample_rate)
            return True

        def initialize(self):
            self.ctx = pyupm_mic.thresholdContext()
            self.ctx.averageReading = 0
            self.ctx.runningAverage = 0
            self.ctx.averagedOver = self._sample_rate


except ImportError:
    logger.warn('pyupm_mic library is missing in the python module path')
    logger.warn('"microphone" type will not be available')


try:
    import pyupm_ldt0028

    class PiezoVibration(Component):
        keyword = 'piezo_vibration'
        connector = 'analogical'

        def get_actuator(self):
            return pyupm_ldt0028.LDT0028(self.pin)

        def get_value(self):
            return self.actuator.getSample()

        value = property(get_value)

except ImportError:
    logger.warn('pyupm_ldt0028 library is missing in the python module path')
    logger.warn('"piezo_vibration" type will not be available')

try:
    import pyupm_buzzer

    class Buzzer(Component):
        keyword = 'buzzer'
        connector = 'digital'

        def __init__(self):
            super(Buzzer, self).__init__()
            self._frequency = 0

        def get_actuator(self):
            return pyupm_buzzer.Buzzer(self.pin)

        def get_value(self):
            return self._frequency

        def set_value(self, value):
            if value <= 0:
                self.actuator.stopSound()
            else:
                self.actuator.playSound(value, 0)
                self._frequency = value

        value = property(get_value, set_value)

except ImportError:
    logger.warn('pyupm_buzzer library is missing in the python module path')
    logger.warn('"buzzer" type will not be available')
    

try:
    import pyupm_mma7660

    class Accelerometer(Component):
        keyword = 'accelerometer'
        connector = 'I2C'
        bus = pyupm_mma7660.MMA7660_I2C_BUS
        address = pyupm_mma7660.MMA7660_DEFAULT_I2C_ADDR


        def get_actuator(self):
            return pyupm_mma7660.MMA7660(self.bus, self.address)

        def initialize(self):
            self.actuator.setModeStandby()
            self.actuator.setSampleRate(pyupm_mma7660.MMA7660.AUTOSLEEP_64)
            self.actuator.setModeActive()

        def _get_raw_value(self):
            x = pyupm_mma7660.new_floatp()
            y = pyupm_mma7660.new_floatp()
            z = pyupm_mma7660.new_floatp()
            self.actuator.getAcceleration(x, y, z)
            return (
                pyupm_mma7660.floatp_value(x),
                pyupm_mma7660.floatp_value(y),
                pyupm_mma7660.floatp_value(z)
            )

        def get_value(self):
            return self._get_raw_value()

        value = property(get_value)


except ImportError:
    logger.warn('pyupm_mma7660 library is missing in the python module path')
    logger.warn('"accelerometer" type will not be available')


def check_layout(layout):
    error = False
    pins = {}
    for comp in layout['components']:
        if comp['pin'] in pins:
            error = True
            logger.error(
                "Component %s overlaps existing %s in pin %s",
                comp['type'],
                pins[comp['pin']]['type'],
                comp['pin']
            )
            continue
        pins[comp['pin']] = comp
    return error


class IntelBoard():
    def __init__(self):
        self.components = {}
        self.events = {}

    @classmethod
    def from_file(cls, file_path):
        if os.path.exists(file_path):
            with open(file_path) as f:
                try:
                    layout = json.loads(f.read())
                except ValueError as e:
                    raise ValueError('File "%s" content is not valid JSON' % file_path)
        else:
            try:
                layout = json.loads(file_path)
            except ValueError as e:
                raise ValueError('String board content is not valid JSON')
        board = cls()
        if check_layout(layout):
            raise ValueError('File "%s" contains reported errors' % file_path)
        for component in layout['components']:
            if not board.register_component(component):
                logger.error('Component %s is not supported', component['type'])
        return board

    def register_component(self, component):
        for cls in Component.__subclasses__():
            if cls.keyword != component['type']:
                continue
            module = cls()
            if not module.set_up(component):
                logger.error('Error setting up component %s', component['name'])
                return False
            self.components[component['name']] = module
            return True
        else:
            return False

    def __getattr__(self, attr):
        logger.debug('Getting attr "%s"', attr)
        if attr in self.components:
            return self.components[attr]
        else:
            logger.warn("Component %s is not defined in board", attr)
            raise AttributeError()

    def __setattr__(self, name, value):
        if 'components' in self.__dict__ and name in self.components:
            logger.debug('Setting internal value of "%s" to "%s"', name, value)
            self.components[name].value = value
        else:
            self.__dict__[name] = value

    @classmethod
    def generate_help(cls):
        for cls in Component.__subclasses__():
            cls.generate_help()

    def loop(self):
        time.sleep(1)
        return True

    def notify_once(self, event, value1=None, value2=None, value3=None):
        current_args = {'value1': value1, 'value2': value2, 'value3': value3}
        if event in self.events and current_args == self.events[event]:
            logger.debug('Skipping sending event %s upstream', event)
            return
        logger.info('Sending event %s upstream', event)
        self.events[event] = current_args
        self._send_event(self, event, current_args)

    def _send_event(self, event, args):
        url = 'https://maker.ifttt.com/trigger/{event}/with/key/{key}' % {
                'event': event,
                'key': self.user_token
        }
        requests.post(url, json=args)

    def sleep(self, t):
        time.sleep(t)



def main():
    IntelBoard.generate_help()

if '__main__' == __name__:
    main()
else:
    parser = argparse.ArgumentParser(description='Intel Board simple API engine')
    parser.add_argument('user_token', help='User token extracted from https://ifttt.com/maker')
    args = parser.parse_args()
    IntelBoard.user_token = args.user_token


