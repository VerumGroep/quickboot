#include "sleep.h"
#include "lib/hal/timer/systick.h"
#include "lib/hal/pwr/pwr.h"
#include "lib/util/util.h"

void sleep(uint32_t period) {
    uint32_t timer = 0;

    __disable_irq();
    while(!timer_expired(&timer, period)) {       
        pwr_enter_sleep_mode();
        __enable_irq();
        __ISB();
        __disable_irq();    
    }

    __enable_irq();
}