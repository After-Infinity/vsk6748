/* Off-board test harness: runs the generated main.c against fake registers and fake kit hardware. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#define VSK_HOST_TEST 1

static struct { uint32_t addr, val; } mem[256]; static int nmem = 0;
static uint32_t *mock_reg(uint32_t a){
    int i; for (i = 0; i < nmem; i++) if (mem[i].addr == a) return &mem[i].val;
    mem[nmem].addr = a; mem[nmem].val = 0; return &mem[nmem++].val;
}
static uint64_t clk = 0; static uint32_t last_out = 0xFFFFFFFFu;
#define OUT8_ADDR 0x01E260B4u
static uint32_t mock_tscl(void){
    uint32_t o = *mock_reg(OUT8_ADDR);
    if (o != last_out) { printf("T %.4f %08X\n", clk / (double)CLK_HZ, o); last_out = o; }
    clk += STEP; return (uint32_t)clk;
}
static uint32_t mock_tsch(void){ return (uint32_t)(clk >> 32); }
#define VSK_REG(a)        (*mock_reg(a))
#define VSK_TSCL_START()  (clk = 0)
#define VSK_TSCL()        mock_tscl()
#define VSK_TSCH()        mock_tsch()

/* ---- fake kit hardware ---- */
static int32_t *adc_in = 0, *rx_in = 0; static int n_adc = 0, n_rx = 0, i_adc = 0, i_rx = 0;
static int calls_ustimer = 0, calls_spi = 0, calls_audio = 0;
static int load(const char *path, int32_t **buf){
    FILE *f = fopen(path, "r"); int cap = 1024, n = 0, v; if (!f) return 0;
    *buf = malloc(cap * sizeof(int32_t));
    while (fscanf(f, "%d", &v) == 1) { if (n == cap) { cap *= 2; *buf = realloc(*buf, cap * sizeof(int32_t)); } (*buf)[n++] = v; }
    fclose(f); return n;
}
static uint16_t vsk_adc_raw(void){ uint16_t v = n_adc ? (uint16_t)adc_in[i_adc % n_adc] : 0; i_adc++; return v; }
#define VSK_DAC_WRITE(v)       printf("D %u\n", (unsigned)(v))
#define VSK_SPI_INIT()         (calls_spi++)
#define VSK_USTIMER_INIT()     (calls_ustimer++)
#define VSK_PLL_CALL(a,b,c,d,e,f,g) printf("PLL %d %d %d %d %d %d %d\n", a,b,c,d,e,f,g)
#define VSK_AUDIO_HW_INIT()    (calls_audio++)
#define VSK_AUDIO_TX_READY()   1
static int32_t rx_next(void){ int32_t v = n_rx ? rx_in[i_rx % n_rx] : 0; i_rx++; return v; }
#define VSK_AUDIO_RX()         rx_next()
#define VSK_AUDIO_TX(v)        printf("A %d\n", (int)(v))

#define main vsk_main
#include GENERATED
#undef main

int main(int argc, char **argv){
    int loops = argc > 1 ? atoi(argv[1]) : 1, i;
    uint32_t in01 = argc > 2 ? (uint32_t)strtoul(argv[2], 0, 16) : 0;
    if (argc > 3 && argv[3][0] != '-') n_adc = load(argv[3], &adc_in);
    if (argc > 4 && argv[4][0] != '-') n_rx  = load(argv[4], &rx_in);
    *mock_reg(0x01E260B0u) = 0xFFFFFFFFu;            /* DIR8 resets to all inputs */
    *mock_reg(0x01E26010u) = 0xFFFFFFFFu;            /* DIR01 */
    *mock_reg(0x01E26020u) = in01;                   /* IN01: switches */
    *mock_reg(0x01C14168u) = 0x11111111u; *mock_reg(0x01C1416Cu) = 0x11111111u; *mock_reg(0x01C14124u) = 0x11111111u;
    vsk_init(); setup();
    for (i = 0; i < loops; i++) loop();
    printf("C %llu\n", (unsigned long long)clk);
    printf("R DIR8 %08X\nR DIR01 %08X\nR PINMUX18 %08X\nR PINMUX19 %08X\nR PINMUX1 %08X\n"
           "R KICK0 %08X\nR KICK1 %08X\nR MDCTL3 %08X\nR PTCMD %08X\nR OUT8 %08X\nR MILLIS %u\n"
           "R CALLS_USTIMER %d\nR CALLS_SPI %d\nR CALLS_AUDIO %d\n",
           *mock_reg(0x01E260B0u), *mock_reg(0x01E26010u), *mock_reg(0x01C14168u), *mock_reg(0x01C1416Cu),
           *mock_reg(0x01C14124u), *mock_reg(0x01C14038u), *mock_reg(0x01C1403Cu),
           *mock_reg(0x01E27000u + 0xA00u + 12u), *mock_reg(0x01E27120u), *mock_reg(OUT8_ADDR),
           (unsigned)millis(), calls_ustimer, calls_spi, calls_audio);
    return 0;
}
