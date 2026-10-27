// Each LED shows the state of the DIP switch with the same number,
// and the loop prints the switch value to the CCS console when it changes.
uint32_t last = 0xFFFFFFFF;

void setup() {
    ledsInit();
    switchesInit();
}

void loop() {
    uint32_t sw = switchesRead();
    ledsWrite(sw);
    if (sw != last) {
        printf("switches = 0x%02X\n", (unsigned)sw);
        last = sw;
    }
}
