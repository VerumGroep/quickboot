#include "uart.h"
#include "lib/hal/rcc/rcc.h"
#include "lib/hal/gpio/gpio.h"
#include "lib/util/util.h"
#include "lib/util/sleep/sleep.h"

void uart_init(struct uart *uart) {
    uint16_t tx = 0;
    uint16_t uartdiv = DEFAULT_CLK_SPEED / USART_BAUDRATE;
    struct gpio *g;
    // int n;
    
    if(uart == USART2) {
        RCC->APB2ENR |= BIT(IOPAEN);
        // RCC->APB2ENR |= BIT(AFIOEN);
        RCC->APB1ENR |= BIT(USART2EN);
        tx = PIN('A', 2);
        // rx = PIN('A', 3);
    }

    // Configure A:2
    g = GPIO(PINBANK(tx));
    // n = PINNO(tx);  
    g->CRL &= ~((3UL << 8) |
                (3UL << 10) |
                (3UL << 12) | 
                (3UL << 14));

    g->CRL |= ((1 << 8) |
                (2 << 10) |
                (0 << 12) | 
                (1 << 14));

    uart->BRR = (uint32_t)((( uartdiv / 16 ) << 4U ) |
                (( uartdiv % 16 ) << 0U ));                   // Set Frequency
    uart->CR1 |= BIT(CR1_RE) | BIT(CR1_TE) | BIT(CR1_UE);     // Enable RX/TX/USART
}

int uart_read_ready(struct uart *uart) {
    return uart->SR & BIT(5);
}

uint8_t uart_read_byte(struct uart *uart) {
    while(!uart_read_ready(uart)) {
        // Do nothing
    }

    return (uint8_t) (uart->DR & 0xff);
}

void uart_read(struct uart *uart, char *buffer, uint32_t length) {
    while(length--) {
        *buffer++ = uart_read_byte(uart);
    }
}

void uart_write_byte(struct uart *uart, uint8_t byte) {
    uart->DR = byte;
    while((uart->SR & BIT(7)) == 0) {}
}

void uart_write(struct uart *uart, char *buffer, uint32_t length) {
    while(length-- > 0) uart_write_byte(uart, *(uint8_t *)buffer++);
}