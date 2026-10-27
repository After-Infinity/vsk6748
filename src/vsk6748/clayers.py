"""C source templates that make up the generated main.c (board layers)."""

C_COMMON = r'''
/* ===================== VSK-6748 Arduino-style layer ===================== */
#include <stdint.h>
#include <stdio.h>
#include <math.h>
#ifndef VSK_HOST_TEST            /* (VSK_HOST_TEST is only for testing off-board) */
#include <c6x.h>
#define VSK_REG(a)        (*(volatile uint32_t *)(a))
#define VSK_TSCL_START()  (TSCL = 0)
#define VSK_TSCL()        (TSCL)
#define VSK_TSCH()        (TSCH)
#endif

/* CPU clock in Hz. Used for delay()/millis()/pacing. If timing is wrong, run:
   python vsk6748.py calibrate <this value> <seconds wanted> <seconds measured> */
#ifndef CPU_HZ
#define CPU_HZ @CPU_HZ@u
#endif

#define LOW     0
#define HIGH    1
#define INPUT   0
#define OUTPUT  1
'''


C_TIMING = r'''
/* ---- timing (uses the CPU cycle counter) ---- */
static void delay(uint32_t ms)
{
    while (ms--) {
        uint32_t s = VSK_TSCL();
        while ((uint32_t)(VSK_TSCL() - s) < (CPU_HZ / 1000u)) { }
    }
}
static void delayMicroseconds(uint32_t us)
{
    while (us--) {
        uint32_t s = VSK_TSCL();
        while ((uint32_t)(VSK_TSCL() - s) < (CPU_HZ / 1000000u)) { }
    }
}
static uint32_t millis(void)
{
    uint64_t t = VSK_TSCL();           /* read TSCL first: it latches TSCH */
    t |= ((uint64_t)VSK_TSCH()) << 32;
    return (uint32_t)(t / (CPU_HZ / 1000u));
}
static uint32_t cyclesNow(void) { return VSK_TSCL(); }
static void cyclesWaitUntil(uint32_t t)   /* wrap-safe wait for a cycle-counter value */
{
    while ((int32_t)(VSK_TSCL() - t) < 0) { }
}
'''


C_GPIO = r'''
/* Pin id = bank*16 + bit. Board pins: */
#define VSK_PIN(bank, bit) ((bank) * 16 + (bit))
#define LED1 VSK_PIN(8, 8)
#define LED2 VSK_PIN(8, 9)
#define LED3 VSK_PIN(8, 10)
#define LED4 VSK_PIN(8, 11)
#define LED5 VSK_PIN(8, 12)
#define LED6 VSK_PIN(8, 13)
#define LED7 VSK_PIN(8, 14)
#define LED8 VSK_PIN(8, 15)
#define SW1  VSK_PIN(0, 0)
#define SW2  VSK_PIN(0, 1)
#define SW3  VSK_PIN(0, 2)
#define SW4  VSK_PIN(0, 3)
#define SW5  VSK_PIN(0, 4)
#define SW6  VSK_PIN(0, 5)
#define SW7  VSK_PIN(0, 6)
#define SW8  VSK_PIN(0, 7)

/* ---- low-level registers ---- */
#define VSK_PSC1_BASE     0x01E27000u
#define VSK_PSC1_PTCMD    VSK_REG(VSK_PSC1_BASE + 0x120u)
#define VSK_PSC1_PTSTAT   VSK_REG(VSK_PSC1_BASE + 0x128u)
#define VSK_PSC1_MDCTL(n) VSK_REG(VSK_PSC1_BASE + 0xA00u + 4u * (n))
#define VSK_LPSC_GPIO     3u
#define VSK_SYSCFG0_BASE  0x01C14000u
#define VSK_KICK0R        VSK_REG(VSK_SYSCFG0_BASE + 0x38u)
#define VSK_KICK1R        VSK_REG(VSK_SYSCFG0_BASE + 0x3Cu)
#define VSK_PINMUX(n)     VSK_REG(VSK_SYSCFG0_BASE + 0x120u + 4u * (n))
#define VSK_GPIO_BASE     0x01E26000u
#define VSK_OFF_DIR 0x0u
#define VSK_OFF_OUT 0x4u
#define VSK_OFF_IN  0x10u

static uint32_t vsk_gpio_reg(uint32_t pin, uint32_t off)
{   /* bank pairs 0/1, 2/3, 4/5, 6/7 and bank 8 sit 0x28 bytes apart from 0x10 */
    return VSK_GPIO_BASE + 0x10u + 0x28u * ((pin >> 4) >> 1) + off;
}
static uint32_t vsk_gpio_mask(uint32_t pin)
{   /* odd banks use the upper 16 bits of the register */
    return 1u << ((pin & 15u) + (((pin >> 4) & 1u) ? 16u : 0u));
}

static void vsk_mux_set(uint32_t reg, uint32_t mask, uint32_t val)
{
    VSK_KICK0R = 0x83E70B13u;  VSK_KICK1R = 0x95A4F1E0u;   /* unlock */
    VSK_PINMUX(reg) = (VSK_PINMUX(reg) & ~mask) | val;
    VSK_KICK0R = 0u;           VSK_KICK1R = 0u;            /* lock   */
}

static void vsk_mux(uint32_t pin)      /* sets GPIO function for known board pins */
{
    static int led_done = 0, sw_done = 0;
    uint32_t bank = pin >> 4, bit = pin & 15u;
    if (bank == 8u && bit >= 8u && !led_done) {
        vsk_mux_set(18, 0xFFFFFF00u, 0x88888800u);
        vsk_mux_set(19, 0x000000FFu, 0x00000088u);
        led_done = 1;
    } else if (bank == 0u && bit < 8u && !sw_done) {
        vsk_mux_set(1, 0xFFFFFFFFu, 0x88888888u);
        sw_done = 1;
    }
}

static void vsk_gpio_init(void)
{
    VSK_PSC1_MDCTL(VSK_LPSC_GPIO) = (VSK_PSC1_MDCTL(VSK_LPSC_GPIO) & ~0x1Fu) | 0x3u;
    VSK_PSC1_PTCMD = 1u;
    while (VSK_PSC1_PTSTAT & 1u) { }
}

/* ---- Arduino-style API ---- */
static void pinMode(uint32_t pin, uint32_t mode)
{
    uint32_t r = vsk_gpio_reg(pin, VSK_OFF_DIR), m = vsk_gpio_mask(pin);
    vsk_mux(pin);
    if (mode == OUTPUT) VSK_REG(r) &= ~m;   /* DIR bit 0 = output */
    else                VSK_REG(r) |= m;    /* DIR bit 1 = input  */
}
static void digitalWrite(uint32_t pin, uint32_t value)
{
    uint32_t r = vsk_gpio_reg(pin, VSK_OFF_OUT), m = vsk_gpio_mask(pin);
    if (value) VSK_REG(r) |= m; else VSK_REG(r) &= ~m;
}
static int digitalRead(uint32_t pin)
{
    return (VSK_REG(vsk_gpio_reg(pin, VSK_OFF_IN)) & vsk_gpio_mask(pin)) ? HIGH : LOW;
}

/* ---- board helpers ---- */
static void ledsInit(void)  { uint32_t i; for (i = 0; i < 8; i++) pinMode(LED1 + i, OUTPUT); }
static void switchesInit(void) { uint32_t i; for (i = 0; i < 8; i++) pinMode(SW1 + i, INPUT); }
static void ledWrite(uint32_t n, uint32_t value) { digitalWrite(LED1 + (n - 1u), value); }  /* n = 1..8 */
static void ledsWrite(uint32_t mask8)           /* bit0 = LED1 ... bit7 = LED8 */
{
    uint32_t r = vsk_gpio_reg(LED1, VSK_OFF_OUT);
    VSK_REG(r) = (VSK_REG(r) & ~0xFF00u) | ((mask8 & 0xFFu) << 8);
}
static uint32_t switchesRead(void)              /* bit0 = SW1 ... bit7 = SW8 (raw pin level) */
{
    return VSK_REG(vsk_gpio_reg(SW1, VSK_OFF_IN)) & 0xFFu;
}
'''


C_KIT = r'''
/* ---- kit layer: DAC / ADC / audio codec ----
   Needs the VSK-6748 common files from your lab (VSK_6748.h on the include path and
   its .c files such as evmc6748.c in the project - Step 8 of the manual). */
#ifndef VSK_HOST_TEST
#include "VSK_6748.h"
uint32_t Spi_inti(void);
uint32_t config_pll0(uint32_t clkmode, uint32_t pllm, uint32_t postdiv, uint32_t plldiv1,
                     uint32_t plldiv2, uint32_t plldiv3, uint32_t plldiv7);
/* DAC1: write a 12-bit value | 0x1000 to SPI1 (as in the manual's DAC experiments) */
#define VSK_DAC_WRITE(v)       do { spi_regs_t *s1_ = (SPI1); s1_->SPIDAT1 = (uint32_t)(v) | 0x1000; } while (0)
/* ADC1 (CH1): write 0x0000 to SPI0, wait for data, read SPIBUF (as in the manual's ADCLOOP) */
static uint16_t vsk_adc_raw(void)
{
    spi_regs_t *s0_ = (SPI0);
    s0_->SPIDAT1 = 0x0000;
    while (CHKBIT(s0_->SPIBUF, RXEMPTY)) { }
    return (uint16_t)s0_->SPIBUF;
}
#define VSK_SPI_INIT()         Spi_inti()
#define VSK_USTIMER_INIT()     USTIMER_init()
#define VSK_PLL_CALL(a,b,c,d,e,f,g) config_pll0(a,b,c,d,e,f,g)
/* McASP start sequence = the manual's testAudioLineIn() (that function is static in evmc6748.c) */
static void vsk_audio_start(void)
{
    SETBIT(MCASP->XGBLCTL, XHCLKRST); while (!CHKBIT(MCASP->XGBLCTL, XHCLKRST)) {}
    SETBIT(MCASP->RGBLCTL, RHCLKRST); while (!CHKBIT(MCASP->RGBLCTL, RHCLKRST)) {}
    SETBIT(MCASP->XGBLCTL, XCLKRST);  while (!CHKBIT(MCASP->XGBLCTL, XCLKRST)) {}
    SETBIT(MCASP->RGBLCTL, RCLKRST);  while (!CHKBIT(MCASP->RGBLCTL, RCLKRST)) {}
    SETBIT(MCASP->XGBLCTL, XSRCLR);   while (!CHKBIT(MCASP->XGBLCTL, XSRCLR)) {}
    SETBIT(MCASP->RGBLCTL, RSRCLR);   while (!CHKBIT(MCASP->RGBLCTL, RSRCLR)) {}
    MCASP->XBUF3 = 0;                 /* no underrun after releasing the state machine */
    SETBIT(MCASP->XGBLCTL, XSMRST);   while (!CHKBIT(MCASP->XGBLCTL, XSMRST)) {}
    SETBIT(MCASP->RGBLCTL, RSMRST);   while (!CHKBIT(MCASP->RGBLCTL, RSMRST)) {}
    SETBIT(MCASP->XGBLCTL, XFRST);    while (!CHKBIT(MCASP->XGBLCTL, XFRST)) {}
    SETBIT(MCASP->RGBLCTL, RFRST);    while (!CHKBIT(MCASP->RGBLCTL, RFRST)) {}
    while (!CHKBIT(MCASP->SRCTL3, XRDY)) {}
    MCASP->XBUF3 = 0;
}
#define VSK_AUDIO_HW_INIT()    do { I2C_init(I2C0, I2C_CLK_400K); MCASP_init(); AIC3106_init(); vsk_audio_start(); } while (0)
#define VSK_AUDIO_TX_READY()   CHKBIT(MCASP->SRCTL3, XRDY)
#define VSK_AUDIO_RX()         (MCASP->@AUDIO_RX@)
#define VSK_AUDIO_TX(v)        (MCASP->XBUF3 = (v))
#endif

static int vsk_ustimer_ready = 0, vsk_kit_ready = 0, vsk_audio_ready = 0;

static void kitInit(void)               /* call once in setup() before dacWrite()/adcRead() */
{
    if (!vsk_kit_ready) {
        if (!vsk_ustimer_ready) { VSK_USTIMER_INIT(); vsk_ustimer_ready = 1; }
        VSK_SPI_INIT();
@PLL_LINE@        vsk_kit_ready = 1;
    }
}
static void dacWrite(uint32_t value12)  /* DAC1, 0..4095 -> about 0..3.3 V */
{
    VSK_DAC_WRITE(value12 & 0x0FFFu);
}
static uint16_t adcRead(void)           /* ADC1 (CH1), 0..4095 */
{
    return (uint16_t)(vsk_adc_raw() & 0x0FFFu);
}

static void audioInit(void)             /* codec + McASP; mic = MIC IN, output = SKR OUT */
{
    if (!vsk_audio_ready) {
        if (!vsk_ustimer_ready) { VSK_USTIMER_INIT(); vsk_ustimer_ready = 1; }
        VSK_AUDIO_HW_INIT();
        vsk_audio_ready = 1;
    }
}
static int32_t audioRead(void)          /* next input word (left/right slots alternate) */
{
    while (!VSK_AUDIO_TX_READY()) { }
    return (int32_t)VSK_AUDIO_RX();
}
static void audioWrite(int32_t v)       /* next output word */
{
    while (!VSK_AUDIO_TX_READY()) { }
    VSK_AUDIO_TX(v);
}
static void audioWriteStereo(int32_t v) { audioWrite(v); audioWrite(v); }   /* same sample, left+right */
'''


C_INIT = r'''
static void vsk_init(void)
{
    VSK_TSCL_START();                  /* start the CPU cycle counter */
@GPIO_INIT@}
'''


C_MAIN = r'''
/* ------------------------------ main ------------------------------ */
int main(void)
{
    vsk_init();
    setup();
    while (1) {
        loop();
    }
}
'''
