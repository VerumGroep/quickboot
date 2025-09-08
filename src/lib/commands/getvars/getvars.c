#include "getvars.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

struct vars current_vars = {
    .num_vars = 11,
    .vars = (struct var[]) {
        {.name = "product", .value = "quickboot"},
        {.name = "build-date", .value = "07-08-2025"},
        {.name = "build-time", .value = "09:35:00 GMT+1"},
        {.name = "production", .value = "yes"},
        {.name = "serial-no", .value = "31337l33t"},        
        {.name = "variant", .value = "ROW"},
        {.name = "soc", .value = "STM32F103RB"},
        {.name = "flash-size", .value = "128KB"},
        {.name = "ram-size", .value = "20KB"},
        {.name = "flash-start-addr", .value = "0x08000000"},
        {.name = "ram-start-addr", .value = "0x20000000"}        
    }
};

uint32_t get_len(struct vars *vars) {
    char buffer[256];
    uint32_t len = 0;

    for (uint32_t i = 0; i < vars->num_vars; i++) {
        int str_len = snprintf(buffer, sizeof(buffer), "%s: %s\n", vars->vars[i].name, vars->vars[i].value);
        if(str_len > 0)
            len += (uint32_t) str_len;
    }

    return len;
}

struct msg *msg_handler_get_vars(struct msg *message) {
    struct msg *response = malloc(sizeof(struct msg));
    uint32_t total_len = get_len(&current_vars);
    (void) message;
        
    memcpy(response->header.magic, MSG_MAGIC, sizeof(MSG_MAGIC));
    response->header.version = MSG_VERSION;
    response->header.type = MSG_TYPE_GET_VARS;
    response->header.len = total_len;
    response->data = malloc(total_len);

    uint32_t offset = 0;
    for (uint32_t i = 0; i < current_vars.num_vars; i++) {        
        int str_len = snprintf(response->data + offset, total_len - offset, "%s: %s\n", 
                 current_vars.vars[i].name, current_vars.vars[i].value);
        if(str_len > 0)
            offset += (uint32_t) str_len;
        
    }

    return response;
}