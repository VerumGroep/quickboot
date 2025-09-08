#include "lib/util/util.h"
#include "pwr.h"

void pwr_enter_sleep_mode() {
    // Clear SLEEPDEEP bit
    SCB->SCR &= ~(BIT(SCR_SLEEPDEEP));
    __DSB();
    __ISB();
    __WFI();
}