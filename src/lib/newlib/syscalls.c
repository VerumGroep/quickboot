#include <stdlib.h>
#include <sys/types.h>
#include "lib/hal/uart/uart.h"
#include "syscalls.h"

int _fstat(int fd, struct stat *st) {
  (void) fd, (void) st;
  return 0;
}

/**
 * @brief Changes the size of the heap
 * 
 * @param len 
 * @return void* 
 */
void *_sbrk(int len) {
    extern char _end;
    extern char __heap_end;
    static unsigned char *heap = NULL;
    unsigned char *prev_heap;

    // Initialize heap at the end of the .bss section
    if (heap == NULL)
        heap = (unsigned char *) &_end;

    if(heap + len >= (unsigned char *) &__heap_end)
      return (void *) -1;

    prev_heap = heap;
    heap += len;
    return prev_heap;
}

int _close(int fd) {
  (void) fd;
  return -1;
}

int _isatty(int fd) {
  (void) fd;
  return 1;
}

int _read(int fd, char *ptr, int len) {
  (void) fd, (void) ptr, (void) len;
  return -1;
}

int _lseek(int fd, int ptr, int dir) {
  (void) fd, (void) ptr, (void) dir;
  return 0;
}

int _write(int fd, char *ptr, int len) {
    if (fd == 1) {
        uart_write(USART2, ptr, (uint32_t) len);
        return len;
    }

    return -1;
}