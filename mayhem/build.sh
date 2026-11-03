#!/usr/bin/env bash
#
# mayhem/build.sh — builds the EKA2L1 loader/common/utils sources (sanitized) into libeka2l1_fuzz.a,
# links one libFuzzer binary + one standalone reproducer per harness, and builds the (unsanitized)
# selftest that mayhem/test.sh runs. The full emulator (≈50 submodules, Qt, Vulkan, ...) is not built:
# the parsers fuzzed here only need the sources below plus apt -dev packages (see mayhem/Dockerfile).
set -euo pipefail

[ -n "${SOURCE_DATE_EPOCH:-}" ] || unset SOURCE_DATE_EPOCH

: "${SANITIZER_FLAGS=-fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer}"
: "${DEBUG_FLAGS:=-g -gdwarf-3}"
: "${CC:=clang}" ; : "${CXX:=clang++}" ; : "${LIB_FUZZING_ENGINE:=-fsanitize=fuzzer}"
: "${MAYHEM_JOBS:=$(nproc)}"
: "${COVERAGE_FLAGS=}"
export SANITIZER_FLAGS DEBUG_FLAGS CC CXX LIB_FUZZING_ENGINE MAYHEM_JOBS COVERAGE_FLAGS

SRC="${SRC:-/mayhem}"
cd "$SRC"

EMU="$SRC/src/emu"
OUT="$SRC/mayhem/build"
HARNESSES="mbm mif rsc gdr svgb nvg e32img fpsx rom sis spi decompress"

rm -rf "$OUT"
mkdir -p "$OUT/gen/common" "$OUT/san" "$OUT/norm"

# Generated headers (upstream's CMake writes these from templates; submodule-free stand-ins).
cat > "$OUT/gen/common/configure.h" <<'H'
#pragma once
#define CURRENT_EKA2L1_VERSION_STRING "0.0.9"
H
cat > "$OUT/gen/common/version.h" <<'H'
#define GIT_BRANCH "mayhem"
#define GIT_COMMIT_HASH "mayhem"
H

INC="-I$OUT/gen -I$EMU/common/include -I$EMU/loader/include -I$EMU/utils/include -I$EMU/mem/include"

SOURCES=$(ls "$EMU"/loader/src/*.cpp \
    "$EMU"/common/src/{virtualmem,wildcard,fileutils,algorithm,bytes,bytepair,chunkyseri,crypt,cvt,dictcomp,flate,log,path,runlen,unicode,hash,types,color,time,region}.cpp \
    "$EMU"/utils/src/{des,uchar,cardinality}.cpp)

compile_one() { # <objdir> <source> <flags...>
    local objdir="$1" src="$2"; shift 2
    local extra=""
    # firmware::block_header is deleted through a base pointer without a virtual destructor, so ASan's
    # new-delete-type-mismatch fires on every parsed block and nothing past the first block is reachable. Sized
    # deallocation is what lets it see the mismatch; dropping it for this one file keeps every other ASan/UBSan
    # check halting. The destructor chain is also inlined into the fpsx harness, which gets the same flag below.
    case "$(basename "$src")" in fpsx.cpp) extra="-fno-sized-deallocation" ;; esac
    $CXX -std=c++20 "$@" $extra $INC -c "$src" -o "$objdir/$(basename "$src" .cpp).o"
}
export -f compile_one
export INC

compile_lib() { # <objdir> <archive> <flags...>
    local objdir="$1" archive="$2"; shift 2
    printf '%s\n' $SOURCES | xargs -P "$MAYHEM_JOBS" -I{} bash -c 'compile_one "$@"' _ "$objdir" {} "$@"
    rm -f "$archive"
    ar rcs "$archive" "$objdir"/*.o
}

LIBS="-lz -lfmt -lspdlog -lre2"

# 1) The project, sanitized, DWARF 3, with SanCov (fuzzer-no-link) so libFuzzer and Mayhem see coverage inside the
#    parsers and not only in the harness translation unit.
compile_lib "$OUT/san" "$OUT/libeka2l1_san.a" -O1 $SANITIZER_FLAGS -fsanitize=fuzzer-no-link $DEBUG_FLAGS

# 2) Each harness twice: libFuzzer engine and the standalone run-once driver.
$CC $SANITIZER_FLAGS $DEBUG_FLAGS -c "$STANDALONE_FUZZ_MAIN" -o "$OUT/standalone_main.o"
$CXX $SANITIZER_FLAGS $DEBUG_FLAGS -c "$SRC/mayhem/lsan_off.cc" -o "$OUT/lsan_off.o"

for h in $HARNESSES; do
    HX=""; [ "$h" = fpsx ] && HX="-fno-sized-deallocation"
    $CXX -std=c++20 -O1 $SANITIZER_FLAGS $DEBUG_FLAGS $HX $INC $LIB_FUZZING_ENGINE \
        "$SRC/mayhem/harnesses/fuzz_$h.cc" "$OUT/lsan_off.o" "$OUT/libeka2l1_san.a" $LIBS \
        -o "/mayhem/fuzz_$h"
    $CXX -std=c++20 -O1 $SANITIZER_FLAGS $DEBUG_FLAGS $HX $INC \
        "$SRC/mayhem/harnesses/fuzz_$h.cc" "$OUT/standalone_main.o" "$OUT/lsan_off.o" "$OUT/libeka2l1_san.a" $LIBS \
        -o "/mayhem/fuzz_$h-standalone"
done

# 3) The oracle: upstream's own loader tests (nvg, gdr, mbm, svgb) plus extra_tests.cc, normal flags, no sanitizers.
compile_lib "$OUT/norm" "$OUT/libeka2l1_norm.a" -O2 $COVERAGE_FLAGS
T="$SRC/src/tests/epoc/loader"
$CXX -std=c++20 -O2 $COVERAGE_FLAGS -I"$SRC/mayhem/selftest" $INC \
    "$SRC/mayhem/selftest/main.cc" "$SRC/mayhem/selftest/extra_tests.cc" \
    "$T/nvg.cpp" "$T/gdr.cpp" "$T/mbm.cpp" "$T/svgb.cpp" \
    "$OUT/libeka2l1_norm.a" $LIBS -o /mayhem/selftest
