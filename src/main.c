/**
 * The Quickboot bootloader
 */

#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include "lib/msg/msg.h"
#include "lib/hal/rcc/rcc.h"
#include "lib/hal/gpio/gpio.h"
#include "lib/hal/timer/systick.h"
#include "lib/hal/uart/uart.h"
#include "lib/hal/pwr/pwr.h"
#include "lib/hal/led/led.h"
#include "lib/newlib/syscalls.h"
#include "lib/util/util.h"
#include "lib/util/sleep/sleep.h"
#include "lib/cmd/cmd.h"
#include "lib/commands/echo/echo.h"
#include "lib/commands/bootloader/bootloader.h"
#include "lib/commands/getvars/getvars.h"
#include "lib/commands/slot/slot.h"

extern void _estack(void);
void _reset(void);
void _exception(void);
void _nmi(void);
void _hardfault(void);
void _memmanage(void);
void _busfault(void);
void _usagefault(void);
void _svcall(void);
void _debugmonitor(void);
void _pendsv(void);

// Table 37. Vector table for STM32F411xC/E
__attribute__((section(".vectors"))) void (*tab[16 + 86])(void) = {
    _estack,
    _reset,
    _nmi,           // NMI
    _hardfault,     // HardFault
    _memmanage,     // MemManage
    _busfault,      // BusFault
    _usagefault,    // UsageFault
    _exception,     // Reserved
    _exception,     // Reserved
    _exception,     // Reserved
    _exception,     // Reserved
    _svcall,        // SVCall
    _debugmonitor,  // Debug Monitor
    _exception,     // Reserved
    _pendsv,        // PendSV
    systick_handler
};

int main(void) {
    // Init user LED
    led_init(&led_green);

    // Set SysTick period to 1ms
    systick_init(DEFAULT_CLK_SPEED / 1000);

    // Initialize USART2        
    uart_init(USART2);
    
    if(msg_init() != 0) {
        uart_write(USART2, "Failed to initialize message system\n", 38);
        return -1;
    }

    // Initialize message handlers
    msg_add_handler(MSG_TYPE_ECHO, msg_handler_echo);
    msg_add_handler(MSG_TYPE_LOCK_STATE, msg_handler_lock_state);
    msg_add_handler(MSG_TYPE_GET_VARS, msg_handler_get_vars);
    msg_add_handler(MSG_TYPE_CURRENT_SLOT, msg_handler_current_slot);
    msg_add_handler(MSG_TYPE_CHANGE_SLOT, msg_handler_change_slot);
    msg_add_handler(MSG_TYPE_BOOT, msg_handler_boot);

    // Blink LED to indicate that we are alive
    for(uint32_t i = 0; i < 4; i++) {
        led_toggle(&led_green);
        sleep(500);
    }
    
    // Main command loop  
    while(true) {       
        sleep(50);                
        read_cmd(USART2);            
    }

    return 0;
}

void e(char *msg) {
    uart_write(USART2, msg, strlen(msg));
}

__attribute__((naked, noreturn)) void _exception(void) {
    e("Unhandled exception ocurred\r\n");    
    _reset();
}

__attribute__((naked, noreturn)) void _nmi(void) {
    e("NMI\n");    
    _reset();
}

__attribute__((naked, noreturn)) void _hardfault(void) {
    e("HardFault\n");    
    _reset();
}

__attribute__((naked, noreturn)) void _memmanage(void) {
    e("MemManage\n");
    _reset();
}

__attribute__((naked, noreturn)) void _busfault(void) {
    e("BusFault\n");    
    _reset();
}

__attribute__((naked, noreturn)) void _usagefault(void) {
    e("UsageFault\n");
    uint32_t *ret = (void *) (0xE000ED28 << 16);
    
    if(*ret & (0x1))
        e(" The processor has attempted to execute an undefined instruction\r\n");    

    if(*ret & (0x1 << 1))
        e(" Instruction executed with invalid EPSR\r\n");

    if(*ret & (0x1 << 2))
        e(" An integrity check error has occurred on EXC_RETURN\n");

    if(*ret & (0x1 << 3))
        e(" A coprocessor access error has occurred\n");

    if(*ret & (0x1 << 8))
        e("Unaligned access error has occurred");

    if(*ret & (0x1 << 9))
        e("Divide by zero error has occurred");

    _reset();
}

__attribute__((naked, noreturn)) void _svcall(void) {
    e("SVCall\n");    
    _reset();
}

__attribute__((naked, noreturn)) void _debugmonitor(void) {
    e("DebugMonitor\n");    
    _reset();
}

__attribute__((naked, noreturn)) void _pendsv(void) {
    e("PendSV\n");
    _reset();
}

__attribute__((naked, noreturn)) void _reset(void) {
    extern long _sdata, _edata, _sbss, _ebss, _sidata;

    // Zero out .bss
    for (long *dst = &_sbss; dst < &_ebss; dst++)
        *dst = 0;

    // Copy data to SRAM
    for (long *dst = &_sdata, *src = &_sidata; dst < &_edata; dst++, src++)
        *dst = *src;

    main();
    for (;;) {}
}
