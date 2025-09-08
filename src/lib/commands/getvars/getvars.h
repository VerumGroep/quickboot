#ifndef HEADER_GETVAR
#define HEADER_GETVAR

#include "lib/msg/msg.h"

struct var {
    char *name;  // Variable name
    char *value; // Variable value
};

struct vars {
    uint32_t num_vars;
    struct var *vars; // List of variables
};

extern struct vars current_vars;

struct msg *msg_handler_get_vars(struct msg*);

#endif