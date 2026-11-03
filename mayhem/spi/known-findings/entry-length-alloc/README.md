# spi: entry name/file lengths are resized without checking them against the input

`spi_entry::do_state` (`src/emu/loader/src/spi.cpp`) reads `name_len` and `rsc_size` as 32-bit values and
immediately calls `name.resize(name_len)` (`spi.cpp:67`) and `file.resize(rsc_size)` (`spi.cpp:75`).
Nothing compares them with the bytes left in the stream, and `chunkyseri::absorb_impl` silently skips a read
that does not fit, so after a short read the next entry is decoded from misaligned bytes and yields
multi-GiB lengths. libFuzzer reports `out-of-memory` (single `malloc` over 2 GiB, or the RSS limit
after two or three of them).

Defects 3522701 (`spi.cpp:67`), 3522576 (`:67`), 3522734 (`:75`), 3522577 (`:75`) and 3521390.
Defect 3521390 has an empty output and no backtrace in Mayhem (libFuzzer's malloc hook fired without
a stack). Replayed here it reproduces: `out-of-memory (malloc(2919235873))`; with
`ASAN_OPTIONS=max_allocation_size_mb=1024` on the standalone binary the allocating frame is
`spi_entry::do_state` `spi.cpp:67`, a 0x747d1020-byte `name.resize`. So it is the same root cause.

Impact: a crafted `.spi` makes the loader allocate gigabytes (denial of service).

Upstream fix: reject entries whose `name_len + rsc_size` exceeds the bytes remaining in the stream before resizing.

Inputs (Mayhem run 2 reproducers, replayed on the commit image):
- `defect-3522701.spi`
- `defect-3522576.spi`
- `defect-3522734.spi`
- `defect-3522577.spi`
- `defect-3521390.spi`

Reproduce:

```
docker run --rm -v "$PWD:/c:ro" <image> /mayhem/fuzz_spi /c/defect-<id>.spi
```
Use the libFuzzer binary: its default 2 GiB malloc/RSS limit is what Mayhem reports as
`out-of-memory`. `/mayhem/fuzz_spi-standalone` has no limit, so on a host with enough memory the
allocation can succeed (or the process is OOM-killed, exit 137); to see the allocating frame there, run it
with `ASAN_OPTIONS=max_allocation_size_mb=1024` (a local diagnostic, not part of the build).
