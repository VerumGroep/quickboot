#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "lib/util/crc32/crc32.h"
#include "lib/hal/uart/uart.h"
#include "lib/msg/msg.h"

#include "bootloader.h"

uint32_t bootloader_unlocked = 0;

struct msg* msg_handler_lock_state(struct msg *message) {
    struct msg *response = malloc(sizeof(struct msg));
    (void) message;

    memset(response, 0, sizeof(struct msg));
    memcpy(response->header.magic, MSG_MAGIC, sizeof(MSG_MAGIC));
    response->header.version = MSG_VERSION;
    response->header.type = MSG_TYPE_LOCK_STATE;
    response->header.len = sizeof(bootloader_unlocked);
    response->data = malloc(sizeof(uint32_t));
    memcpy(response->data, &bootloader_unlocked, response->header.len);
    
    return response;
}

struct msg* msg_handler_boot(struct msg *message) {
    struct msg *response = malloc(sizeof(struct msg));    
    struct bootloader_image *image = (struct bootloader_image *) message->data;
    uint32_t overflow = 0;
    void *buffer = NULL;

    memset(response, 0, sizeof(struct msg));
    memcpy(response->header.magic, MSG_MAGIC, sizeof(MSG_MAGIC));
    response->header.version = MSG_VERSION;
    response->header.type = MSG_TYPE_ERROR;        
    response->header.len = 0;
    response->data = NULL;   

    // 1. Do not exceed max image size
    if(image->size > BOOTLOADER_MAX_IMAGE_SIZE) {        
        response->header.flags |= MSG_IMAGE_TOO_LARGE;        
        overflow = image->size - BOOTLOADER_MAX_IMAGE_SIZE;
        image->size = BOOTLOADER_MAX_IMAGE_SIZE;
    }

    // 2. Read overflowed bytes to clear UART buffer
    if(overflow > 0) {
        for(uint32_t i = 0; i < overflow; i++) {
            uart_read_byte(USART2);         
        }
    }

    // 3. Allocate memory for the image
    buffer = malloc(image->size);
    if(buffer == NULL) {        
        response->header.flags |= MSG_OUT_OF_MEMORY;        
        goto exit;
    }
    
    // 4. Read image into buffer
    uart_read(USART2, buffer, image->size);
    
    // 5. Check CRC32 
    uint32_t calculated_crc = crc32(buffer, image->size);
    if(calculated_crc != image->crc32) {        
        response->header.flags |= MSG_INVALID_CRC;        
        goto exit;
    }

    // 6. Check the bootloader lock state
    if(!bootloader_unlocked) {        
        response->header.flags |= MSG_BOOTLOADER_LOCKED;    
        goto exit;
    }

    // 7. Boot!!
    void (*entrypoint)() = (void (*)()) buffer + 1;
    entrypoint();

    // We should never get here ...
    response->header.type = MSG_TYPE_BOOT;    

    exit:
    free(buffer);
    return response;    
}