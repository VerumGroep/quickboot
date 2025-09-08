#include "led.h"
#include "lib/hal/gpio/gpio.h"

struct led led_green = {
    .pin = PIN('A', 5),
    .state = LED_OFF
};

void led_init(struct led *led) {    
    gpio_set_mode(led->pin, GPIO_OUTPUT);
}

void led_toggle(struct led *led){
    led->state = !led->state;
    gpio_write(led->pin, led->state);
}