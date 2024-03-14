from threading import Lock, Thread
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


class Button:

    def __init__(self, pin) -> None:
        GPIO.setup(pin, GPIO.IN)
        self._pin = pin

    def isPressed(self) -> bool:
        """
        Return is the button is pressed

        Returns:
            bool: if the button is pressed
        """
        return GPIO.input(self._pin) == GPIO.HIGH
        
    def __str__(self) -> str:
        return "Button - " + str(self._pin)

class Relay:

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

    def getTextToDisplay(self, lowerIndex):
        """
        Get the portion of text to display

        Args:
            lowerIndex (int): index of the first letter to start in the text to display
        """
        upperIndex = lowerIndex + self._maxDisplaySize
        if (upperIndex < len(self._currentText)):
            # Tout ce qui est retourné fait parti du texte
            return self._currentText[lowerIndex:(lowerIndex+self._maxDisplaySize)]
        elif upperIndex >= len(self._currentText) and upperIndex < (len(self._currentText) + self._textPadding):
            # Si on a une partie du texte, mais on ajoute des espaces avant de repasser le texte
            text = self._currentText[lowerIndex:]
            while (len(text) < self._maxDisplaySize):
                text += ' '
            return text
        elif upperIndex >= (len(self._currentText) + self._textPadding) and lowerIndex < (len(self._currentText) + self._textPadding):
            # Le texte est entièrement passé (ou presque) et il faut réaficher le début du texte
            text = ""
            if (lowerIndex < len(self._currentText)):
                text += self._currentText[lowerIndex:]
                for i in range(0, self._textPadding):
                    text += ' '
            else:
                for i in range(0, self._textPadding - (lowerIndex - len(self._currentText))):
                    text += ' '
            upperIndex = upperIndex % (len(self._currentText) + self._textPadding)
            text += self._currentText[:upperIndex]
            return text

    def getMenuText(self):
        """
        Get the menu text (to add aftewards on the LCD)
        """
        if (self._maxDisplaySize == 16):
            menuBar = ""
            if (self._arrowDisplayed == 0 or self._arrowDisplayed == 1):
                menuBar += "<"
            else:
                menuBar += " "
            menuBar += "    X    V    "
            if (self._arrowDisplayed == 0 or self._arrowDisplayed == 2):
                menuBar += ">"
            else:
                menuBar += " "
            return menuBar
        return ""

    def t_scrollText(self):
        lastTextLoaded = self._currentText
        while (self._isThreadRuning):
            self.home()
            self.setLCDParam()
            if (lastTextLoaded != self._currentText):
                indexToStart = 0
                lastTextLoaded = self._currentText

            if (self._lockDisplayThread.acquire(blocking=False)):
                self._lockDisplayThread.release()
                if ((len(self._currentText)) > self._maxDisplaySize):
                    if (self._maxDisplaySize == 16):
                        self.writeText(self.getTextToDisplay(indexToStart), False)
                        self.writeText("\n" + self.getMenuText())
                    else:
                        self.writeText(self.getTextToDisplay(indexToStart))

                    indexToStart += 1
                    if (indexToStart == (len(self._currentText) + self._textPadding)):
                        indexToStart = 0
                else:
                    if (self._maxDisplaySize == 16):
                        self.writeText(self._currentText, False)
                        self.writeText("\n" + self.getMenuText())
                    else:
                        self.writeText(self._currentText)
            time.sleep(.2)


    def setText(self, text):
        """
        Set the current message without clear the lcd 

        Args:
            text (str): text to add
        """
        while len(text) < 32: #clears the rest of the screen
            text += ' '
        self._lockDisplayThread.acquire(blocking=True)
        self._currentText = text
        self._maxDisplaySize = 32
        self._lockDisplayThread.release()

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
        self._lockDisplayThread.acquire(blocking=True)
        self._arrowDisplayed = arrowDisplayed
        self._currentText = text
        self._maxDisplaySize = 16
        self._lockDisplayThread.release()

    def quit(self):
        """
        Exit the programm
        """
        time.sleep(0.2)
        self._isThreadRuning = False
        self._displayThread.join()

    def __init__(self, textAddress):
        self._textAddress = textAddress

        ### INITIAL CONFIG
        self._textPadding = 6
        self._currentText = ""
        self._maxDisplaySize = 32
        self._arrowDisplayed = 0
        self._isThreadRuning = True
        
        self._lockDisplayThread: Lock = Lock()
        self._displayThread = Thread(target=self.t_scrollText)
        self._displayThread.start()


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

class Core(metaclass=Singleton): 

    def __init__(self):
        GPIO.setmode(GPIO.BCM)

        self._buttons: list[Button] = []
        self._relays: list[Relay] = []
        self._lcd: LCD = None

        ### INITIAL CONFIG
        btns_pins = [27, 22, 23, 24] # Buttons wired on pins 13, 15, 16, 18
        relays_pins = [12, 13, 16, 26] # Relays wired on pins 32, 33, 36, 37
        lcd_rgb_adress = 0x62 # Bus address to change the RGB value for the LCD
        lcd_text_adress = 0x3e # Bus address to change the text value for the LCD

        print("pins buttons = " + str(btns_pins))
        print("pins relais = " + str(relays_pins))

        for i in range(0, len(btns_pins)):
            btn = Button(pin=btns_pins[i])
            print("Add button : " + str(btn))
            self._buttons.append(btn)

        for i in range(0, len(relays_pins)):
            relais = Relay(pin=relays_pins[i])
            print("Add relais : " + str(relais))
            self._relays.append(relais)

        self._lcd = RGBLCD(lcd_text_adress, lcd_rgb_adress)
        self._lcd.setRGB(0,255,0)
        self._lcd.setText("Initialisation ended")

    def getBackButton(self) -> Button:
        return self._buttons[0]
    def getForwardButton(self) -> Button:
        return self._buttons[3]
    def getCancelButton(self) -> Button:
        return self._buttons[1]
    def getValidateButton(self) -> Button:
        return self._buttons[2]
    
    def getNorthenPump(self):
        return self._relays[0]
    def getEasternPump(self):
        return self._relays[1]
    def getSouthernPump(self):
        return self._relays[2]
    def getWesternPump(self):
        return self._relays[3]

    def setText(self, text):
        self._lcd.setText(text)
    def setMenuText(self, text, arrowDisplayed=0):
        self._lcd.setMenuText(text, arrowDisplayed)
    def setColor(self, r, g, b):
        if (isinstance(self._lcd, RGBLCD)):
            self._lcd.setRGB(r, g, b)

    def quit(self):
        self._lcd.quit()


if __name__ == "__main__":
    import random

    core = Core()

    time.sleep(.2)

    core._lcd.setMenuText("Press button to test, OK ?")

    while True:
        try:
            for i in range (len(core._buttons)):
                if (core._buttons[i].isPressed()):
                    core._relays[i].toggle()
                    core.setColor(random.randrange(0,255,1),random.randrange(0,255,1),random.randrange(0,255,1))
                    core.setText("toggle {} by {}".format(str(core._relays[i]), str(core._buttons[i])))

            time.sleep(.15)

        except KeyboardInterrupt:
            for i in range(len(core._relays)):
                core._relays[i].off()

            core.setColor(255,0,30)
            core.setText("Bye bye ^^ !")
            core.quit()
            print("exit")
            exit(1)
