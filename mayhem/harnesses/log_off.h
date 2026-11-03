#pragma once

#include <common/log.h>

#include <memory>

// The emulator's LOG_* macros dereference log::filterings, which only setup_log() creates (and that
// opens EKA2L1.log). Install a filter that passes nothing instead, so no logger or file is needed.
inline void mayhem_log_off() {
    static const bool done = [] {
        eka2l1::log::filterings = std::make_unique<eka2l1::log_filterings>();
        eka2l1::log::filterings->reset_all(spdlog::level::off);
        return true;
    }();
    (void)done;
}
