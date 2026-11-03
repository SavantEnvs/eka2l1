# rsc: a compressed resource whose lookup entry refers to itself recurses until the stack is exhausted

`rsc_file_legacy::read_internal` (`src/emu/loader/src/rsc.cpp:719`) handles the "lookup" bit pattern by calling
`read_internal(lookup_id + 1, buffer, true)`. `lookup_id` is a bit-field read from the file and the lookup
offset table is also from the file, so a lookup entry can resolve to a range that contains the same lookup
code, and nothing bounds the nesting. About 240 `read_internal` frames later ASan reports `stack-overflow`
(innermost frame `read_bits`, `rsc.cpp:609`/`:610`).

Defects 3522783 and 3522777 (CWE-400). Same root cause, two innermost frames.

Impact: loading a crafted legacy compressed `.rsc` crashes the emulator (denial of service).

Upstream fix: carry a recursion depth in `read_internal` (or reject a lookup range that includes the one being decoded) and fail past a small limit.

Inputs (Mayhem run 2 reproducers, replayed on the commit image):
- `defect-3522783.rsc`
- `defect-3522777.rsc`

Reproduce:

```
docker run --rm -v "$PWD:/c:ro" <image> /mayhem/fuzz_rsc-standalone /c/defect-<id>.rsc
```
Exits 1 with `AddressSanitizer: stack-overflow`.
