/* Minimal PIC18F4550 core. Pin numbers 0..7 map to PORTB bits RB0..RB7. */
#include "Arduino.h"

static volatile unsigned long picduino_millis_counter = 0;
static uint8_t picduino_uart_started = 0;

void pinMode(uint8_t pin, uint8_t mode) {
    if (pin > 7) return;
    if (mode == OUTPUT) {
        TRISB &= (uint8_t)~(1u << pin);
    } else {
        TRISB |= (uint8_t)(1u << pin);
        if (mode == INPUT_PULLUP) INTCON2bits.RBPU = 0;
    }
}

void digitalWrite(uint8_t pin, uint8_t value) {
    if (pin > 7) return;
    if (value == LOW) LATB &= (uint8_t)~(1u << pin);
    else LATB |= (uint8_t)(1u << pin);
}

int digitalRead(uint8_t pin) {
    if (pin > 7) return LOW;
    return (PORTB & (uint8_t)(1u << pin)) ? HIGH : LOW;
}

void delay(unsigned long ms) {
    while (ms--) __delay_ms(1);
}

/* Hardware UART1: TX=RC6, RX=RC7. 20 MHz crystal, 16-bit BRG,
   BRGH=1 gives SPBRG=42 for approximately 116279 baud (about +0.94%). */
void serial_begin(unsigned long baud) {
    TRISCbits.TRISC6 = 0;
    TRISCbits.TRISC7 = 1;
    TXSTA = 0x24;       /* TXEN=1, BRGH=1, asynchronous */
    RCSTA = 0x90;       /* SPEN=1, CREN=1 */
    BAUDCONbits.BRG16 = 1;
    if (baud == 0) baud = 115200UL;
    /* rounded divisor for BRG16 + BRGH: Fosc/(4*(SPBRG+1)) */
    {
        unsigned long divisor = (F_CPU + (2UL * baud)) / (4UL * baud);
        if (divisor < 1) divisor = 1;
        divisor -= 1;
        SPBRGH = (uint8_t)(divisor >> 8);
        SPBRG = (uint8_t)divisor;
    }
    picduino_uart_started = 1;
}

void serial_print(const char *text) {
    if (!picduino_uart_started) serial_begin(115200UL);
    while (*text) {
        while (!PIR1bits.TXIF) { }
        TXREG = (uint8_t)*text++;
    }
}

void serial_println(const char *text) {
    serial_print(text);
    while (!PIR1bits.TXIF) { }
    TXREG = '\r';
    while (!PIR1bits.TXIF) { }
    TXREG = '\n';
}

int serial_available(void) {
    if (!picduino_uart_started) serial_begin(115200UL);
    if (RCSTAbits.OERR) { RCSTAbits.CREN = 0; RCSTAbits.CREN = 1; }
    return PIR1bits.RCIF ? 1 : 0;
}

int serial_read(void) {
    if (!serial_available()) return -1;
    if (RCSTAbits.FERR) { volatile uint8_t discard = RCREG; (void)discard; return -1; }
    return RCREG;
}

/* millis() remains a placeholder until timer interrupts are implemented. */
unsigned long millis(void) { return picduino_millis_counter; }

void main(void) {
    /* Disable analog functions on shared pins where applicable; actual clock and
       configuration bits must be programmed for the specific PICduino hardware. */
    ADCON1 = 0x0F;
    CMCON = 0x07;
    LATB = 0x00;
    TRISB = 0xFF;
    setup();
    for (;;) loop();
}
