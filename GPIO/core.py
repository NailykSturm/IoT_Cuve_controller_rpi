import RPi.GPIO as GPIO
import time, sys

from utils import Singleton

if sys.platform == 'uwp':
    import winrt_smbus as smbus
    bus = smbus.SMBus(1)
else:
    import smbus
    import RPi.GPIO as GPIO
    rev = GPIO.RPI_REVISION
    if rev == 2 or rev == 3:
        bus = smbus.SMBus(1)
    else:
        bus = smbus.SMBus(0)

class Core(metaclass=Singleton): 

    class Button:

        def __init__(self, pin) -> None:
            GPIO.setup(pin, GPIO.IN)
            self._pin = pin
            self._lastValue = self.isPressed()

        def isPressed(self) -> bool:
            """
            Return is the button is pressed

            Returns:
                bool: if the button is pressed
            """
            self._lastValue = GPIO.input(self._pin) == GPIO.HIGH
            return self._lastValue

        def isChanged(self):
            """
            Check if the button has changed his state

            Returns:
                bool: if the current state is not he same as in memory
            """
            return GPIO.input(self._pin) != self._lastValue
        
        def __str__(self) -> str:
            return "Button - " + str(self._pin)

    class Relais:

        def __init__(self, pin) -> None:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
            self._pin = pin
            self._value = GPIO.LOW

        def on(self):
            """
            Set the relay to on
            """
            GPIO.output(self._pin, GPIO.HIGH)
            self._value = GPIO.HIGH

        def off(self):
            """
            Set the relay to off
            """
            GPIO.output(self._pin, GPIO.LOW)
            self._value = GPIO.LOW

        def toggle(self):
            """
            Toggle the relay (invert the current state)
            """
            if (self._value == GPIO.LOW):
                self.on()
            else:
                self.off()

        def __str__(self) -> str:
            return "Relais - " + str(self._pin)
    
    class LCD:
        def __init__(self, textAddress):
            self._textAddress = textAddress

        def textCommand(self, cmd):
            """
            Send a command to the LCD

            Args:
                cmd (hexa): command to send to the lcd (see doc for list of available command) [ex: 0x01]
            """
            bus.write_byte_data(self._textAddress,0x80,cmd)
        
        def clear(self):
            """
            Clear the message displayed on the LCD
            """
            self.textCommand(0x01) # clear display

        def home(self):
            """
            Set the position of the lcd cursor to home
            """
            self.textCommand(0x02) # return home

        def setLCDParam(self):
            """
            Default setter of the LCD parameters

            Tell the LCD to not display cursor, and have 2 lines 
            """
            time.sleep(.05)
            self.textCommand(0x08 | 0x04) # display on, no cursor
            self.textCommand(0x28) # 2 lines
            time.sleep(.05)

        def writeText(self, text, autoWrap=True):
            """
            Write text on the LCD

            Note : The maximum displayed character is 32

            Args:
                text (str): Text to display
                autoWrap (bool, optional): Auto return to line if the text is > 16 characters. Defaults to True.
            """
            count = 0
            row = 0
            for c in text:
                if (autoWrap):
                    if c == '\n' or count == 16:
                        count = 0
                        row += 1
                        if row == 2:
                            break
                        self.textCommand(0xc0)
                        if c == '\n':
                            continue
                count += 1
                bus.write_byte_data(self._textAddress,0x40,ord(c))

        def setText(self, text, autoWrap=True):
            """
            Clear the old text and replace it by the newest

            Args:
                text (str): Text to display
                autoWrap (bool, optional): Auto return to line if the text is > 16 characters. Defaults to True.
            """
            self.clear()
            self.setLCDParam()
            self.writeText(text, autoWrap)

        def setTextNoRefresh(self, text):
            """
            Set the current message without clear the lcd 

            Args:
                text (str): text to add
            """
            self.home()
            self.setLCDParam()
            while len(text) < 32: #clears the rest of the screen
                text += ' '
            self.writeText(text)

        def setMenuText(self, text, arrowDisplayed=0):
            """
            Set a menu label, with the text on the first line and a navigation menu on the second

            Ex:
            Config : 
            <    X    V    >

            Args:
                text (str): Text to display
                arrowDisplayed (int, optional): Number and position of arrow to display in the menu 0 = Both (<>) 1 = Right (< ) 2 = Left ( >) 3 = None (  ). Defaults to 0.
            """
            if (arrowDisplayed > 4 or arrowDisplayed < 0):
                raise ValueError
            menuBar = ""

            if (arrowDisplayed == 0 or arrowDisplayed == 1):
                menuBar += "<"
            else:
                menuBar += " "
            menuBar += "    X    V    "
            if (arrowDisplayed == 0 or arrowDisplayed == 2):
                menuBar += ">"
            else:
                menuBar += " "

            self.clear()
            self.setLCDParam()
            self.writeText(text, False)
            self.writeText("\n" + menuBar)


    class RGBLCD(LCD):
        def __init__(self, textAddress, rgbAddress) -> None:
            super().__init__(textAddress)
            self._rgbAddress = rgbAddress

        def setRGB(self, r, g, b):
            """
            Set the RGB value of the LCD screen

            Args:
                r (int): Red value (from 0 to 255)
                g (int): Green value (from 0 to 255)
                b (int): Blue value (from 0 to 255)
            """
            bus.write_byte_data(self._rgbAddress, 0, 0)
            bus.write_byte_data(self._rgbAddress, 1, 0)
            bus.write_byte_data(self._rgbAddress, 0x08, 0xaa)
            bus.write_byte_data(self._rgbAddress, 4, r)
            bus.write_byte_data(self._rgbAddress, 3, g)
            bus.write_byte_data(self._rgbAddress, 2, b)


    def __init__(self):
        GPIO.setmode(GPIO.BCM)

        self._buttons: list[self.Button] = []
        self._relais: list[self.Button] = []
        self._lcd: self.LCD = None

        # btns_pins = [13,15,16,18]
        # relais_pins = [32,33,36,37]
        btns_pins = [27, 22, 23, 24]
        relais_pins = [12, 13, 16, 26]
        lcd_rgb_adress = 0x62
        lcd_text_adress = 0x3e


        print("pins buttons = " + str(btns_pins))
        print("pins relais = " + str(relais_pins))

        for i in range(0, len(btns_pins)):
            btn = self.Button(pin=btns_pins[i])
            print("Add button : " + str(btn))
            self._buttons.append(btn)

        for i in range(0, len(relais_pins)):
            relais = self.Relais(pin=relais_pins[i])
            print("Add relais : " + str(relais))
            self._relais.append(relais)

        self._lcd = self.RGBLCD(lcd_text_adress, lcd_rgb_adress)
        self._lcd.setRGB(0,255,0)
        self._lcd.setText("Initialisation ended")


if __name__ == "__main__":
    import random

    core = Core()

    core._lcd.setMenuText("Press button to test, OK ?")

    while True:
        try:
            for i in range (len(core._buttons)):
                if (core._buttons[i].isPressed()):
                    core._relais[i].toggle()
                    core._lcd.setRGB(random.randrange(0,255,1),random.randrange(0,255,1),random.randrange(0,255,1))
                    core._lcd.setTextNoRefresh("toggle "+ str(core._relais[i]))

            time.sleep(.15)

        except KeyboardInterrupt:
            for i in range(len(core._relais)):
                core._relais[i].off()

            core._lcd.setRGB(255,0,30)
            core._lcd.setText("Bye bye ^^ !")
            print("exit")
            exit(1)