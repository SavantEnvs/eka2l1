#include "log_off.h"
#include <common/chunkyseri.h>
#include <loader/spi.h>

#include <cstdint>
#include <vector>

using namespace eka2l1;

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t *data, std::size_t size) {
    mayhem_log_off();
    if (size < 16) {
        return -1;
    }

    std::vector<std::uint8_t> copy(data, data + size);
    common::chunkyseri seri(copy.data(), copy.size(), common::SERI_MODE_READ);
    loader::spi_file spi(loader::SPI_UID);
    spi.do_state(seri);
    return 0;
}
