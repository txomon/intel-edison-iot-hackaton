from intel_board import IntelBoard

ib = IntelBoard.from_file('board_layout.json')

while ib.loop():
    if ib.light_sensor > 40:
        ib.notify_once("light", "on")
    else:
        ib.notify_once("light", "off")
