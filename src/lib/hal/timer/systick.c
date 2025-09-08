#include "lib/util/util.h"
#include "lib/hal/rcc/rcc.h"
#include "systick.h"
#include <stdio.h>

static volatile uint32_t s_ticks;

void systick_init(uint32_t ticks) {
    if((ticks - 1) > 0xffffff)
        return;

    SYSTICK->STCSR = BIT(STCSR_ENABLE)  | \
                     BIT(STCSR_TICKINT) | \
                     BIT(STCSR_CLKSOURCE);
    SYSTICK->STRVR = ticks - 1;
    SYSTICK->STCVR = 0;
    // RCC->APB2ENR |= BIT(SYSCFGEN);    
}

void systick_handler() {
    s_ticks++;
}

void delay(uint32_t ms) {
    uint32_t end = s_ticks + ms;
    while(s_ticks < end) {}
}

bool timer_expired(uint32_t *t, uint32_t period) {    
    // Integer overflow, time is wrapped
    if ((s_ticks + period) < *t)
        *t = 0;

    // First iteration
    if (*t == 0)
        *t = s_ticks + period;

    // Timer not yet expired
    if (*t > s_ticks)
        return false;

    // Set next expiration time
    *t = (s_ticks - *t) > period ? s_ticks + period : *t + period;

    return true;
}