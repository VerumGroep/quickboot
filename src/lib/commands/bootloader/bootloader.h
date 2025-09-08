#ifndef HEADER_BOOTLOADER
#define HEADER_BOOTLOADER

#include <stdint.h>
#include "lib/msg/msg.h"

#define BOOTLOADER_MAX_IMAGE_SIZE 4096 // 4KB

struct bootloader_image {    
    uint32_t size;
    uint32_t crc32;
};

struct msg *msg_handler_lock_state(struct msg*);
struct msg *msg_handler_boot(struct msg*);

#endif