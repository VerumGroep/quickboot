#include "crc32.h"

uint32_t crc32(const uint8_t *data, uint32_t length) {
    uint32_t crc = 0xFFFFFFFF;
    uint32_t poly = 0xEDB88320;

    for (uint32_t i = 0; i < length; ++i) {
        crc ^= data[i];
        for (int bit = 0; bit < 8; ++bit) {
            if (crc & 1)
                crc = (crc >> 1) ^ poly;
            else
                crc >>= 1;
        }
    }

    return crc ^ 0xFFFFFFFF;
}