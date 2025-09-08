#ifndef HEADER_SLOT
#define HEADER_SLOT

extern char slot[1];

struct msg *msg_handler_current_slot(struct msg*);
struct msg *msg_handler_change_slot(struct msg*);

#endif