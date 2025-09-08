#ifndef HEADER_TIMER_SYSTICK
#define HEADER_TIMER_SYSTICK

#include <stdint.h>
#include <stdbool.h>

#define SYSTICK_BASE 0xE000E010

enum { STCSR_ENABLE, STCSR_TICKINT, STCSR_CLKSOURCE, STCSR_COUNTFLAG = 16 };

struct systick {
    volatile uint32_t STCSR;
    volatile uint32_t STRVR;
    volatile uint32_t STCVR;
    volatile uint32_t STCR;
};

#define SYSTICK ((struct systick *) SYSTICK_BASE)

void systick_init(uint32_t ticks);
void systick_handler();
void delay(uint32_t ms);
bool timer_expired(uint32_t *t, uint32_t period);
#endif