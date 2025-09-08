/**
 * Communication between the host and the target is
 * done using a standardized messaging format. The
 * system is designed to be asynchronous. Messages
 * are not expected to be received in any specific 
 * order.
 * 
 * Both the host and the target implement a message
 * inbox and outbox. The host periodically polls the
 * target for new messages. New messages are retreived,
 * re-ordered and processed. 
 */

#ifndef HEADER_MSG
#define HEADER_MSG

#include <stdint.h>

#include "lib/hal/uart/uart.h"

#define MSG_MAGIC "MSG!"
#define MSG_VERSION 1

#define MSG_MAX_HANDLERS 10
#define MSG_MAX_MESSAGES 10
#define MSG_MAX_PAYLOAD_SIZE 128

#define MSG_FLAG_ORIGIN_HOST    1
#define MSG_FLAG_ORIGIN_TARGET  (1 << 1)
#define MSG_INVALID (1 << 2)
#define MSG_INVALID_MAGIC (1 << 3)
#define MSG_INVALID_VERSION (1 << 4)
#define MSG_INVALID_CRC (1 << 5)
#define MSG_INVALID_PAYLOAD_SIZE (1 << 6)
#define MSG_NO_HANDLER (1 << 7)
#define MSG_INVALID_SLOT (1 << 8)
#define MSG_BOOTLOADER_LOCKED (1 << 9)
#define MSG_IMAGE_TOO_LARGE (1 << 10)
#define MSG_OUT_OF_MEMORY (1 << 11)

enum msg_types {
    MSG_TYPE_ERROR,
    MSG_TYPE_ECHO,
    MSG_TYPE_LOCK_STATE,
    MSG_TYPE_GET_VARS,
    MSG_TYPE_CURRENT_SLOT,
    MSG_TYPE_CHANGE_SLOT,
    MSG_TYPE_BOOT,
    MSG_TYPE_EMPTY
};

/**
 * Standardized message header format
 * 
 * Each message starts with a version number to check if
 * the client actually supports the protocol.
 * 
 * A unique identifier is generated for each transaction,
 * this can happen on the client or target side. The flags
 * indicate where the message originated from.
 * 
 * We support up-to 256 unique message types. Each message
 * can be of arbitrary length. A CRC32 checksum is
 * calculated over each message to ensure its integrity.
 */
struct msg_header {
    unsigned char magic[4]; // Magic value to identify the message format
    uint32_t version;   // Protocol version
    uint32_t id;        // Message identifier
    uint32_t type;      // Message type
    uint32_t flags;     // Message specific flags
    uint32_t len;       // Length of the message data
    uint32_t crc32;     // crc32 of the message data        
};

/**
 * The actual message is stored in a queue before it is
 * processed by the application. We store the message
 * header and a pointer to the actual data.
 * 
 * On the target side this can be tricky since we would
 * need to write/use an allocator to store data of
 * arbitrary sizes.
 * 
 * It is reasonable to assume that data is overwritten
 * when you encounter a message with the same pointer
 * value. Because the target is likely storing the
 * information at a static offset.
 * 
 */
struct msg {
    struct msg_header header;     // Message header
    void *data;                   // Data pointer
};

/**
 * Holds a list of received messages
 */
struct msgbox {
    uint32_t num_messages;
    uint32_t next_id;
    struct msg messages[MSG_MAX_MESSAGES];
};

struct msg_handler {
    uint32_t type;
    void *handler;
};

struct msg_handlers {
    uint32_t num_handlers;
    struct msg_handler handlers[MSG_MAX_HANDLERS];
};

extern struct msgbox *inbox;
extern struct msgbox *outbox;
extern struct msg_handlers *handlers;

int32_t msg_init();
int32_t msg_add_handler(uint32_t, void *);
void msg_write(struct uart *uart);
void msg_read(struct uart *uart);
void msg_process();

#endif