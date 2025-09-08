#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

#include "cmd.h"
#include "lib/msg/msg.h"
#include "lib/util/sleep/sleep.h"
#include "lib/hal/gpio/gpio.h"
#include "lib/hal/uart/uart.h"
#include "lib/hal/led/led.h"

void read_cmd(struct uart * uart) {
    struct cmd c = {0};
    uart_read(uart, (char *)&c, sizeof(struct cmd));
    
    switch(c.type) {
        case CMD_MSG_WRITE:
            msg_write(uart);            
            break;
        case CMD_MSG_READ:
            msg_read(uart);
            break;
        case CMD_MSG_LIST:
            // Send number of messages
            uart_write(uart, (char *) &outbox->num_messages, sizeof(uint32_t));

            // Send each message header
            for(uint32_t i = 0; i < outbox->num_messages; i++)
                uart_write(uart, (char *) &outbox->messages[i].header, sizeof(struct msg_header));             

            break;
    }

    msg_process();
}