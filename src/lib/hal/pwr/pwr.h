#ifndef HEADER_PWR
#define HEADER_PWR

#include <stdint.h>

enum {
    SCR_SLEEPONEXIT = 1,
    SCR_SLEEPDEEP,
    SCR_SEVONPEND = 4
};

struct scb {
    volatile uint32_t CPUID;
    volatile uint32_t ICSR;
    volatile uint32_t VTOR;    
    volatile uint32_t AIRCR;
    volatile uint32_t SCR;
    volatile uint32_t CCR;
    volatile uint32_t SHPR1;
    volatile uint32_t SHPR2;
    volatile uint32_t SHPR3;
    volatile uint32_t SHCSR;
    volatile uint32_t CFSR;
    volatile uint32_t HFSR;
    volatile uint32_t DFSR;
    volatile uint32_t MMFAR;
    volatile uint32_t BFAR;
    volatile uint32_t AFSR;
    volatile uint32_t RESERVED1[17];
    volatile uint32_t CPACR;
    volatile uint32_t RESERVED2; 
};

#define SCB ((struct scb *) 0xE000ED00)

void pwr_enter_sleep_mode();

#endif