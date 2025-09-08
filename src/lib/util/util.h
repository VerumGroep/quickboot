#ifndef HEADER_UTIL
#define HEADER_UTIL

#define DEFAULT_CLK_SPEED 8000000
#define BIT(x) (1UL << (x))

#define __disable_irq() __asm volatile("cpsid i" : : : "memory")
#define __enable_irq() __asm volatile("cpsie i" : : : "memory")
#define __DSB() __asm volatile("dsb 0xf" : : : "memory")
#define __ISB() __asm volatile("isb 0xf" : : : "memory")
#define __WFI() __asm volatile("wfi")

#endif