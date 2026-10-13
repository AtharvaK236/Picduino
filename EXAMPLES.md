# Example sketches

The examples are intended as first tests for the early PICduino core. They are not proof of full Arduino compatibility.

## Blink

File: `Board Files/picduino/PICduino/libraries/PICduinoExamples/examples/Blink/Blink.ino`

```cpp
#define LED_PIN 0

void setup() {
  pinMode(LED_PIN, OUTPUT);
}

void loop() {
  digitalWrite(LED_PIN, HIGH);
  delay(1000);
  digitalWrite(LED_PIN, LOW);
  delay(1000);
}
```

What it does:
1. Selects logical pin `0` as an output.
2. Turns it on for one second.
3. Turns it off for one second.
4. Repeats forever.

In the current variant header, logical D0 maps to RB0. Confirm the mapping and LED polarity against your actual board.

## UART LED Reply

File: `Board Files/picduino/PICduino/libraries/PICduinoExamples/examples/UART_LED_Reply/UART_LED_Reply.ino`

This sketch starts serial at nominal 115200 baud and prints `PICduino UART READY`. It polls for two incoming characters. If it receives `hi`, it prints `hello host` and turns the LED on; otherwise, it turns the LED off.

For a simple test:
1. Upload the sketch using a compatible bootloader.
2. Open a serial terminal at 115200 baud, 8-N-1.
3. Send the two characters `hi`.
4. Look for `hello host` and observe the LED.

**Clock warning:** the supplied core calculates UART timing using `F_CPU`; the board definition currently says 48 MHz while the core defaults to 20 MHz. Resolve this mismatch before relying on baud rate or delays.

## Supported subset

The current build tool performs text-based translation for a small sketch subset and maps these calls:

- `Serial.begin(...)`
- `Serial.print(...)`
- `Serial.println(...)`
- `Serial.available()`
- `Serial.read()`

Do not assume support for arbitrary C++, templates, classes, lambdas, all Arduino APIs, or third-party Arduino libraries. Check `picduino_build.py` before using an API that is not shown in these examples.
