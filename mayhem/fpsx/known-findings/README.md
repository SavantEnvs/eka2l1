# fpsx known finding: `block_header` has no virtual destructor

`src/emu/loader/include/loader/fpsx.h` holds block headers in a `std::unique_ptr<block_header>`
(`header_`) and assigns derived types (`block_header_binary`, `block_header_core_cert`, ...) to it, but
`block_header` has a non-virtual destructor. With sized deallocation (clang's C++14+ default) ASan
reports `new-delete-type-mismatch` on every block of every valid image, so the parser can never get past
the first block: any valid seed (including `new-delete-type-mismatch.fpsx`, a core image) aborts at load.

Mitigation: `mayhem/build.sh` compiles `fpsx.cpp` and the fpsx harness with `-fno-sized-deallocation`
only. ASan and every other UBSan check stay halting; no other file is affected. The finding is real
upstream UB (deleting a derived object through a base pointer without a virtual destructor).

Reproduce: build `fpsx-standalone` without `-fno-sized-deallocation` and run it on the file here.
