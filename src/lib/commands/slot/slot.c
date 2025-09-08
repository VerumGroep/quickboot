#include "lib/msg/msg.h"
#include <string.h>
#include <stdlib.h>

unsigned char slot[1] = {"a"};

struct msg *msg_handler_current_slot(struct msg *message) {
    struct msg *response = malloc(sizeof(struct msg));    
    (void) message;

    memset(response, 0, sizeof(struct msg));
    memcpy(response->header.magic, MSG_MAGIC, sizeof(MSG_MAGIC));
    response->header.version = MSG_VERSION;
    response->header.type = MSG_TYPE_CURRENT_SLOT;
    response->header.len = 1;
    response->data = malloc(1);
    ((unsigned char *) response->data)[0] = slot[0];
    
    return response;
}

struct msg *msg_handler_change_slot(struct msg *message) {
    struct msg *response = malloc(sizeof(struct msg));   
     
    memset(response, 0, sizeof(struct msg));
    memcpy(response->header.magic, MSG_MAGIC, sizeof(MSG_MAGIC));
    response->header.type = MSG_TYPE_CHANGE_SLOT;
    
    unsigned char new_slot = ((unsigned char *) message->data)[0];    
    if(new_slot != 'a' && new_slot != 'b') {
        response->header.version = MSG_VERSION;
        response->header.type = MSG_TYPE_ERROR;        
        response->header.flags |= MSG_INVALID_SLOT;   
        response->header.len = 0;            
        return response;
    }

    response->header.len = 1;
    response->data = malloc(1);
    ((unsigned char *) slot)[0] = new_slot;
    ((unsigned char *) response->data)[0] = new_slot;
        
    return response;
}