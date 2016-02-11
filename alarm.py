from intel_board import IntelBoard
import signal
import sys


board_layout = '''
{
        "components": [
                {
                        "type": "microphone",
                        "name": "mic",
                        "pin": "A1"
                },
		{
                        "type": "rotary",
                        "name": "rotary",
                        "pin": "A0"
                },
		{	
                        "type": "buzzer",
                        "name": "buzzer",
                        "pin": "D6"
                },
		{
                        "type": "temperature",
                        "name": "temp",
                        "pin": "A3"
                },
		{
                        "type": "led",
                        "name": "green_led",
                        "pin": "D2"
                },
		{
                        "type": "led",
                        "name": "red_led",
                        "pin": "D4"
                },
		{
                        "type": "led",
                        "name": "blue_led",
                        "pin": "D3"
                }		
        ]
} '''
ib = IntelBoard.from_file(board_layout)

def cleanup(a, b):
    ib.green_led = False
    ib.blue_led = False
    ib.red_led = False
    ib.buzzer = 0
    sys.exit(0)
signal.signal(signal.SIGINT, cleanup)


print "****** Fire Alarm ******"
# init
ib.buzzer = 0

while True:
    ib.green_led = True
    ib.blue_led = False
    ib.red_led = False
    while ib.rotary > 150:
        ib.blue_led = True
        ib.green_led = False
	noise_level = ib.mic.get_value()
	if ( noise_level > 100 ):
            print "Current Noise level is {0}".format(noise_level)
            ib.red_led = True
            ib.blue_led = False
            ib.buzzer = 100
            ib.notify_once("robbed")
    ib.buzzer = 0



