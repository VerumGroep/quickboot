#include <util/util.h>
#include <string.h>
#include <stdlib.h>
#include <stdbool.h>

#include "lib/util/crc32/crc32.h"
#include "msg.h"

struct msgbox *inbox;
struct msgbox *outbox;
struct msg_handlers *handlers;
uint32_t last_message_id = 0;

int32_t msg_init() {    
    inbox = malloc(sizeof(struct msgbox));
    outbox = malloc(sizeof(struct msgbox));
    handlers = malloc(sizeof(struct msg_handlers));
    
    if (!inbox || !outbox || !handlers)
        return -1;
    
    memset(inbox, 0, sizeof(struct msgbox));
    memset(outbox, 0, sizeof(struct msgbox));
    memset(handlers, 0, sizeof(struct msg_handlers));
    inbox->next_id = 1; // Start IDs from 1
    outbox->next_id = 1; // Start IDs from 1            
    return 0;
}

int32_t msg_add_handler(uint32_t type, void *handler) {
    if(handlers->num_handlers >= (MSG_MAX_HANDLERS - 1))
        return -1;

    handlers->handlers[handlers->num_handlers].type = type;
    handlers->handlers[handlers->num_handlers].handler = handler;
    handlers->num_handlers++;    
    return 0;
}

void msg_store(struct msg *message, struct msgbox *destination) {
    uint32_t index = destination->num_messages;
    
    // We've reached the maximum number of messages
    // next message will be stored at the start
    if(index >= (MSG_MAX_MESSAGES - 1)) {
        index = 0;
        destination->num_messages = 0;
    }

    // Assign message identifier
    message->header.id = destination->next_id;
    destination->next_id++;

    // Read the current message at this index
    // free its data if it exists
    if(destination->messages[index].data != NULL) {
        free(destination->messages[index].data);        
        destination->messages[index].data = NULL;
        destination->messages[index].header.type = MSG_TYPE_EMPTY;
        destination->messages[index].header.crc32 = 0;
        destination->messages[index].header.len = 0;        
    }

    // Copy to messagebox    
    memcpy(&destination->messages[index], message, sizeof(struct msg));
    destination->num_messages++;
    free(message);
}

void msg_store_inbox(struct msg *message) {
    return msg_store(message, inbox);
}

void msg_store_outbox(struct msg *message) {
    return msg_store(message, outbox);
}

void msg_write(struct uart *uart) {    
    struct msg *message = malloc(sizeof(struct msg));
    if(!message)
        return;

    // 0. Read up until the magic value
    char magic[4];
    uart_read(uart, magic, sizeof(magic));

    while(memcmp(magic, MSG_MAGIC, sizeof(MSG_MAGIC) - 1) != 0) {
        // If we don't have the magic value, read another byte
        memcpy(magic, magic + 1, sizeof(magic) - 1);
        uart_read(uart, &magic[sizeof(magic) - 1], 1);
    }

    // 1. Initially read the size of a msg_header struct
    memset(message, 0, sizeof(struct msg));    
    memcpy(message->header.magic, MSG_MAGIC, sizeof(MSG_MAGIC));
    uart_read(uart, (char *) message + sizeof(magic), sizeof(struct msg_header) - sizeof(magic));

    // 2. Check if we received a message of the correct version
    if(message->header.version != MSG_VERSION) {
        message->header.type = MSG_TYPE_ERROR;
        message->header.flags |= MSG_INVALID;
        message->header.flags |= MSG_INVALID_VERSION;        
        goto exit;
    }

    // 3. Read the payload    
    uint32_t overflow = 0;
    if(message->header.len > MSG_MAX_PAYLOAD_SIZE) {
        overflow = message->header.len - MSG_MAX_PAYLOAD_SIZE;
        message->header.type = MSG_TYPE_ERROR;
        message->header.flags |= MSG_INVALID;
        message->header.flags |= MSG_INVALID_PAYLOAD_SIZE;
        message->header.len = MSG_MAX_PAYLOAD_SIZE;
    }   

    // Allocate memory for the payload
    message->data = malloc(message->header.len);    
    if (!message->data)
        return;
        
    uart_read(uart, (char *) message->data, message->header.len);

    // Discard any overflow bytes
    if(overflow > 0) {
        for(uint32_t i = 0; i < overflow; i++) {
            uart_read_byte(uart);         
        }
    }
    
    // 4. Check if the CRC of the payload matches
    if(crc32(message->data, message->header.len) != message->header.crc32) {
        message->header.type = MSG_TYPE_ERROR;
        message->header.flags |= MSG_INVALID;
        message->header.flags |= MSG_INVALID_CRC;
        goto exit;        
    }
    
    exit:
        // An error occurred, store in outbox
        (message->header.flags & MSG_INVALID) != 0 ? msg_store_outbox(message) : msg_store_inbox(message);        
}

void msg_read(struct uart *uart) {    
    uint32_t id;
    uart_read(uart, (char *) &id, sizeof(uint32_t));

    for(uint32_t i = 0; i < outbox->num_messages; i++) {
        if(outbox->messages[i].header.id == id) {
            uart_write(uart, (char *) outbox->messages[i].data, outbox->messages[i].header.len);
            outbox->messages[i].header.type = MSG_TYPE_EMPTY;
            
            if(outbox->messages[i].data != NULL) {
                free(outbox->messages[i].data);                                                
                outbox->messages[i].data = NULL;                 
                outbox->messages[i].header.crc32 = 0;
                outbox->messages[i].header.len = 0;                
            }            

            return;    
        }
    }
}

void msg_process() {    
    for(uint32_t i = 0; i < inbox->num_messages; i++) {        
        struct msg *message = &inbox->messages[i];
        if(message->header.id > last_message_id) {           

            bool handler_found = false;
            for(uint32_t j = 0; j < MSG_MAX_HANDLERS; j++) {
                if (message->header.type == MSG_TYPE_ERROR)
                    break; // Skip error messages

                if(handlers->handlers[j].type == message->header.type) {
                    struct msg *(*handler)(struct msg*) = (struct msg*(*)(struct msg*)) handlers->handlers[j].handler;                    
                    if(handler == NULL)
                        break;

                    struct msg *new_message = handler(message);
                    new_message->header.crc32 = crc32(new_message->data, new_message->header.len),         
                    msg_store_outbox(new_message);
                    handler_found = true;      
                }
            }

            if(!handler_found) {
                // No handler found, store in outbox as an error
                struct msg *new_message = malloc(sizeof(struct msg));
                memcpy(new_message, message, sizeof(struct msg));

                // Copy payload
                new_message->data = malloc(message->header.len);
                memcpy(new_message->data, message->data, message->header.len);
                
                new_message->header.type = MSG_TYPE_ERROR;                
                new_message->header.flags |= MSG_NO_HANDLER;
                new_message->header.crc32 = crc32(new_message->data, new_message->header.len);
                msg_store_outbox(new_message);
            }
            
            last_message_id = message->header.id;            
             
            // Done processing, free memory
            if(message->data != NULL) {
                free(message->data);
                message->data = NULL;
                message->header.crc32 = 0;
                message->header.len = 0;
            }
        }        
    }
}