#ifndef HEADER_CMD
#define HEADER_CMD

#include <stdint.h>
#include "lib/hal/uart/uart.h"

enum { CMD_MSG_WRITE, CMD_MSG_READ, CMD_MSG_LIST };

struct __attribute__((packed)) cmd {
    uint32_t type;
    uint32_t length;    
};

void read_cmd(struct uart *);

#endif