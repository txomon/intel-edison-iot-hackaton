from __future__ import print_function
import argparse
try:
    import simplejson as json
except ImportError:
    import json
import logging
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
            return False
        if not self.register_custom(component):
            return False
        self.actuator = self.get_actuator()
        return True

    def register_custom(self, component):
        return True
    
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

    @classmethod
    def generate_help(cls):
        print("Module %s doesn't have documentation"% cls.__name__)

try:
    import mock
    pyupm_grove = mock.Mock()
    #import pyupm_grove

    class GroveLed(Component):
        keyword = 'led'
        connector = 'digital'

        def __init__(self):
            super(GroveLed, self).__init__()
            self._value = False

        def get_actuator(self):
            return pyupm_grove.GroveLed(self.pin)

        def set_value(self, new_value):
            if new_value:
                self._value = True
                self.actuator.on()
            else:
                self._value = False
                self.actuator.off()

        def get_value(self):
            logger.debug('Returning led state %b', self._value)
            return self._value


    class GroveButton(Component):
        keyword = 'button'
        connector = 'digital'

        def get_actuator(self):
            return pyupm_grove.GroveButton(self.pin)

        def get_value(self):
            return self.actuator.value()


    class GroveLight(Component):
        keyword = 'light_sensor'
        connector = 'analogical'

        def get_actuator(self):
            return pyupm_grove.GroveLight(self.pin)

        def get_value(self):
            return self.actuator.value()


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


    class GroveRotary(Component):
        keyword = 'rotary'
        connect = 'analogical'

        def get_actuator(self):
            return pyupm_grove.GroveRotary(self.pin)

        def get_value(self):
            return self.actuator.abs_deg()


    class GroveSlide(Component):
        keyword = 'slide'
        connect = 'analogical'

        def __init__(self):
            self._ref = 5

        def get_actuator(self):
            return pyupm_grove.GroveSlide(self.pin, self.ref)

        def get_value(self):
            return self.actuator.value()

        ref = property(lambda s: s._ref)
                   
        def register_custom(self, component):
            self._ref = component.get('ref', 5)


    class GroveTemp(Component):
        keyword = 'temperature'
        connect = 'analogical'

        def get_actuator(self):
            return pyupm_grove.GroveSlide(self.pin)

        def get_value(self):
            return self.actuator.value()

except ImportError:
    logger.warn('pyupm_grove library is missing in the python module path')
    logger.warn('"led", "button", "light_sensor", "relay", "rotary", "slide"'
            ' and "temperature" types will not be available')

try: 
    import pyupm_mic

    class Microphone(Component):
        keyword = 'microphone'
        connect = 'analogical'

        def __init__(self):
            self.threshold = 20

        def get_actuator(self):
            return pyupm_mic.Microphone(self.pin)

        def get_value(self):
            sample_buffer = pyupm_mic.uint16Array(20)
            ctx = pyupm_mic.thresholdContext()
            self.actuator.getSampledWindow(20, 5, sample_buffer)
            return self.actuator.findThreshold(ctx, self.threshold, sample_buffer, 20)

        def register_custom(self, component):
            self.threshold = component.get('threshold', 20)


except ImportError:
    logger.warn('pyupm_mic library is missing in the python module path')
    logger.warn('"microphone" type will not be available')


try:
    import pyupm_ldt0028

    class PiezoVibration(Component):
        keyword = 'piezo_vibration'
        connect = 'analogical'

        def get_actuator(self):
            return pyupm_ldt0028.LDT0028(self.pin)

        def get_value(self):
            return self.actuator.getSample()

except ImportError:
    logger.warn('pyupm_ldt0028 library is missing in the python module path')
    logger.warn('"piezo_vibration" type will not be available')



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
        with open(file_path) as f:
            try:
                layout = json.loads(f.read())
            except ValueError as e:
                raise ValueError('File "%s" content is not valid JSON' % file_path)
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
                return False
            self.components[component['name']] = module
            return True
        else:
            return False

    def __getattr__(self, attr):
        logger.debug('Getting attr "%s"', attr)
        if  attr in self.components:
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



def main():
    IntelBoard.generate_help()

if '__main__' == __name__:
    main()
else:
    parser = argparse.ArgumentParser(description='Intel Board simple API engine')
    parser.add_argument('user_token', help='User token extracted from https://ifttt.com/maker')
    args = parser.parse_args()
    IntelBoard.user_token = args.user_token


