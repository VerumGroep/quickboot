#ifndef HEADER_GPIO
#define HEADER_GPIO

#include <stdint.h>
#include <stdbool.h>

#define GPIO_BASE_ADDR 0x40010800
#define GPIO_BANK_SIZE 0x400

#define GPIO(bank) ((struct gpio *) (GPIO_BASE_ADDR + (GPIO_BANK_SIZE * bank)))
#define PIN(bank, number) (((bank - 'A') << 8) | number)
#define PINBANK(pin) (pin >> 8)
#define PINNO(pin) (pin & 0xff)

enum { 
    GPIO_INPUT,
    GPIO_OUTPUT,
    GPIO_OUTPUT_2MHZ,
    GPIO_OUTPUT_50MHZ
 };

struct gpio {
    volatile uint32_t CRL;
    volatile uint32_t CRH;
    volatile uint32_t IDR;
    volatile uint32_t ODR;
    volatile uint32_t BSRR;
    volatile uint32_t LCKR;
};

void gpio_set_mode(uint16_t pin, uint8_t mode);
void gpio_write(uint16_t pin, bool value);
void gpio_set_af(uint16_t pin);
#endif