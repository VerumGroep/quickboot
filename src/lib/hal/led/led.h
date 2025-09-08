#ifndef HEADER_LED
#define HEADER_LED

#include <stdint.h>
#include <stdbool.h>

#include "lib/hal/gpio/gpio.h"

#define LED_OFF 0
#define LED_ON 1

struct led {
    uint16_t pin;
    bool state;
};

extern struct led led_green;

void led_init(struct led *led);
void led_toggle(struct led *led);

#endif