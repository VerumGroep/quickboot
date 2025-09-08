#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include "gpio.h"
#include "lib/hal/rcc/rcc.h"
#include "lib/util/util.h"

void gpio_set_mode(uint16_t pin, uint8_t mode) {    
    struct gpio *g = GPIO(PINBANK(pin));    
    int n = PINNO(pin);

    RCC->APB2ENR |= BIT(PINBANK(pin) + 2);
    // Set CNF
    g->CRL &= ~(3U << ((n * 4) + 2));

    // Set MODE
    g->CRL &= ~(3U << (n * 4));
    g->CRL |= (mode & 3U) << (n * 4);
}

void gpio_write(uint16_t pin, bool value) {
    struct gpio *g = GPIO(PINBANK(pin));
    g->BSRR = (1U << PINNO(pin)) << (value ? 0 : 16);
}

void gpio_set_af(uint16_t pin) {    
    struct gpio *g = GPIO(PINBANK(pin));
    int n = PINNO(pin);    
    
    // Set CNF
    g->CRL &= ~(3U << ((n * 4) + 2));
    g->CRL |= (2U & 3U) << ((n * 4) + 2);

    // Set MODE
    g->CRL &= ~(3U << (n * 4));
    g->CRL |= (3U) << (n * 4);
    
    return;
}

