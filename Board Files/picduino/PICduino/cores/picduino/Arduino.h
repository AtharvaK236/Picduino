#ifndef PICDUINO_ARDUINO_H
#define PICDUINO_ARDUINO_H

#include <xc.h>
#include <stdint.h>
#include <stdbool.h>
#include "../../variants/pic18f4550/pins_arduino.h"

#ifndef F_CPU
#define F_CPU 20000000UL
#endif
#ifndef _XTAL_FREQ
#define _XTAL_FREQ F_CPU
#endif

#define LOW 0
#define HIGH 1
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2

#ifdef __cplusplus
extern "C" {
#endif
void pinMode(uint8_t pin, uint8_t mode);
void digitalWrite(uint8_t pin, uint8_t value);
int digitalRead(uint8_t pin);
void delay(unsigned long ms);
unsigned long millis(void);
void serial_begin(unsigned long baud);
void serial_print(const char *text);
void serial_println(const char *text);
int serial_available(void);
int serial_read(void);
void setup(void);
void loop(void);
#ifdef __cplusplus
}
#endif
#endif
