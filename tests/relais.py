import RPi.GPIO as GPIO

class GroveRelay():
    
    def __init__(self, pin):
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
        self._pin = pin

    def on(self):
        GPIO.output(self._pin, GPIO.HIGH)

    def off(self):
        GPIO.output(self._pin, GPIO.LOW)

def main():
    import sys
    import time

    if len(sys.argv) < 2:
        print('Usage: {} pin'.format(sys.argv[0]))
        sys.exit(1)

    relay = GroveRelay(int(sys.argv[1]))

    while True:
        try:
            relay.on()
            time.sleep(1)
            relay.off()
            time.sleep(1)
        except KeyboardInterrupt:
            relay.off()
            print("exit")
            exit(1)      

if __name__ == "__main__":
    main()