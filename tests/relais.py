import RPi.GPIO as GPIO

class GroveRelay():
    
    def __init__(self, pin):
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
        self._value = GPIO.LOW
        self._pin = pin

    def on(self):
        GPIO.output(self._pin, GPIO.HIGH)
        self._value = GPIO.HIGH

    def off(self):
        GPIO.output(self._pin, GPIO.LOW)
        self._value = GPIO.LOW

    def toggle(self):
        if (self._value == GPIO.LOW):
            self.on()
        else:
            self.off()

class Button():
    def __init__(self, pin):
        GPIO.setup(pin, GPIO.IN)
        self._pin = pin

    def isPressed(self):
        return GPIO.input(self._pin) == GPIO.HIGH

relais_pins = [16, 18, 24, 26]

def main():
    import time

    GPIO.setmode(GPIO.BCM)

    relay0 = GroveRelay(relais_pins[0])
    relay1 = GroveRelay(relais_pins[1])
    relay2 = GroveRelay(relais_pins[2])
    relay3 = GroveRelay(relais_pins[3])
    btn = Button(22)

    relais = [relay0, relay1, relay2, relay3]

    relais_todo = 0

    while True:
        try:
            if (btn.isPressed()):
                relais[relais_todo].toggle()
                relais_todo = (relais_todo + 1) % len(relais_pins)

            time.sleep(0.5)
        except KeyboardInterrupt:
            relay0.off()
            relay1.off()
            relay2.off()
            relay3.off()
            print("exit")
            exit(1)

if __name__ == "__main__":
    main()