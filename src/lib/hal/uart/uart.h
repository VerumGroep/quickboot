#ifndef HEADER_UART
#define HEADER_UART

#include <stdint.h>

#define USART_BAUDRATE 115200

// Section 19.6 USART registers
struct uart { 
    volatile uint32_t SR;
    volatile uint32_t DR;
    volatile uint32_t BRR;
    volatile uint32_t CR1;
    volatile uint32_t CR2;
    volatile uint32_t CR3;
    volatile uint32_t GTPR;
};

// Section 19.6.4 Control register 1 (USART_CR1)
enum {
    CR1_SBK,
    CR1_RWU,
    CR1_RE,
    CR1_TE,
    CR1_IDLEIE,
    CR1_RXNEIE,
    CR1_TCIE,
    CR1_TXEIE,
    CR1_PEIE,
    CR1_PS,
    CR1_PCE,
    CR1_WAKE,
    CR1_M,
    CR1_UE    
};

#define USART2 ((struct uart *) 0x40004400) // PA9(TX/AF7) - PA10(RX/AF7)

void uart_init(struct uart *uart);
int uart_read_ready(struct uart *uart);
uint8_t uart_read_byte(struct uart *uart);
void uart_read(struct uart *uart, char *buffer, uint32_t length);
void uart_write_byte(struct uart *uart, uint8_t byte);
void uart_write(struct uart *uart, char *buffer, uint32_t length);
void uart_flush(struct uart *uart);
#endif