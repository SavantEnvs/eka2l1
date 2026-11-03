#include <catch2/catch.hpp>

#include "../harnesses/log_off.h"

int main() {
    mayhem_log_off();
    return selftest::run_all();
}
