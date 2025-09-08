#ifndef HEADER_SYSCALLS
#define HEADER_SYSCALLS

#include <sys/stat.h>

int _fstat(int fd, struct stat *st);
void *_sbrk(int len);
int _close(int fd);
int _isatty(int fd);
int _read(int fd, char *ptr, int len);
int _lseek(int fd, int ptr, int dir);

#endif