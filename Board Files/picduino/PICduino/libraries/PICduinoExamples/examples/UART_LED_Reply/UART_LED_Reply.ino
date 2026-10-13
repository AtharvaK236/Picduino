#define LED_PIN 0

char received[2];
unsigned char count = 0;

void setup() {
  pinMode(LED_PIN, OUTPUT);
  Serial.begin(115200);
  Serial.println("PICduino UART READY");
}

void loop() {
  // Poll UART continuously so incoming commands are not delayed by long waits.
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (count < 2) {
      received[count++] = c;
    }

    if (count == 2) {
      if (received[0] == 'h' && received[1] == 'i') {
        Serial.println("hello host");
        digitalWrite(LED_PIN, HIGH);
      } else {
        digitalWrite(LED_PIN, LOW);
      }
      count = 0;
    }
  }
}
