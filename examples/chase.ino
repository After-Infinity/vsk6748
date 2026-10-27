// One LED at a time, left to right, then back
void setup() {
    ledsInit();
}

void loop() {
    int i;
    for (i = 0; i < 8; i++) { ledsWrite(1u << i); delay(100); }
    for (i = 6; i > 0; i--) { ledsWrite(1u << i); delay(100); }
}
