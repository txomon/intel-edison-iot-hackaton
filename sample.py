from intel_board import IntelBoard

ib = IntelBoard.from_file('board_layout.json')

ib.blue_led.ref = True
