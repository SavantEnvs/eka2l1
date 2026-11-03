# rom: directory cycle recurses until the stack is exhausted

`read_rom_entry` (`src/emu/loader/src/rom.cpp:199`) calls `read_rom_dir` (`rom.cpp:220`) for every directory
entry, seeking to `rom_to_offset(rom_base, entry.address_lin)`. `address_lin` is read from the file, so a
directory entry can point at one of its own ancestors, and nothing tracks depth or visited directories. The
two functions recurse about 240 frames deep and ASan reports `stack-overflow`.

These are the CWE-400 defects of the `rom` target: 7 in run 3 (3576389, 3522803, 3522623, 3522622,
3522618, 3522620, 3522621) and 4 more that only run 2 filed (3522619, 3522695, 3522769, 3522795; not
reproduced in run 3, their inputs stay here). They are **stack exhaustion, not OOM**; Mayhem files them under
"Uncontrolled Resource Consumption" and the innermost frame varies (`operator new`, `__asan_memset`,
`rom_dir()`, `basic_string::_M_mutate`, ...) with whichever call happens to cross the guard page, so the same
recursion gets a new defect id when a different frame crosses it (3576389 is `operator new` /
`__new_allocator<rom_entry>::allocate` under `read_rom_dir` `rom.cpp:220`). One root cause.

Impact: loading a crafted ROM image crashes the emulator (denial of service).

Upstream fix: pass a depth counter (or a set of visited `address_lin` values) down `read_rom_entry`/`read_rom_dir` and stop when it is exceeded.

Inputs (Mayhem reproducers, replayed on the commit image; each one exits with `stack-overflow`, whichever id
Mayhem files it under, since the crossing frame depends on the environment). `defect-3576389.rom` is the
input Mayhem lists for run-3 defect 3576389; it is byte-identical to `defect-3522622.rom`:
- `defect-3522803.rom`
- `defect-3522795.rom`
- `defect-3522769.rom`
- `defect-3522695.rom`
- `defect-3522623.rom`
- `defect-3522622.rom`
- `defect-3522618.rom`
- `defect-3522619.rom`
- `defect-3522620.rom`
- `defect-3522621.rom`
- `defect-3576389.rom`

Reproduce:

```
docker run --rm -v "$PWD:/c:ro" <image> /mayhem/fuzz_rom-standalone /c/defect-<id>.rom
```
Exits 1 with `AddressSanitizer: stack-overflow`.
