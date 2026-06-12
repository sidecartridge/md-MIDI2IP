; User firmware module — MIDI-to-IP
; (C) 2026 by Diego Parrilla
; License: GPL v3
;
; EPIC-01 (hooks) + a cable-free loopback bring-up.
;
; STORY-01 installs the BIOS (trap #13) vector using the XBRA convention (see
; below). MIDI Maze does ALL its MIDI ring I/O through the BIOS device-3 calls
; (Bconstat / Bconin / Bconout) — NOT XBIOS — so the BIOS hook is the only one
; we need, and it acts AS the MIDI device: Bconstat(3) reports whether the RP
; has a byte, Bconin(3) pops one from the RP, Bconout(3) ships one to the RP.
; No Iorec, no ACIA. In the loopback bring-up the RP echoes OUT->IN, making a
; "ring of one": MIDI Maze sends 0x00, reads its own 0x00 back, becomes MASTER.
; EPIC-03 replaces the echo with the network ring.
;
; XBRA (eXtended BRanch Administration)
; -------------------------------------
; Each handler is preceded by a 12-byte XBRA header: dc.l 'XBRA', a cookie
; ('SDMI'), and the previous vector (the chain target). The <old> field is
; in cartridge ROM (which the m68k can't write), so the install path hands
; the original vector and the field's address to the RP, which patches the
; field in the served ROM image (rp/src/midi.c). Mirrors md-drives-emulator's
; GEMDRIVE/FLOPPY.

ROM4_ADDR            equ $FA0000

; --- MIDI app command namespace (must match rp/src/include/midi.h) ---
; The only MIDI command left is the boot-time save-vector; OUT/IN are the
; commemul fast path (EPIC-09), so the EPIC-02 per-byte CMD_MIDI_SEND/RECV
; commands are retired.
APP_MIDI             equ $0300
CMD_MIDI_SAVE_VECTOR equ (APP_MIDI + 0)          ; $0300: patch a ROM longword field

; Shared MIDI-IN fields in the APP_FREE arena, written by the RP and read by the
; m68k (which owns no state in the ROM region):
MIDI_IN_STATUS_ADDR  equ (ROM4_ADDR + $2300)     ; $FA2300: pre-baked Bconstat (-1 ready / 0 none); also the Bconin ready flag
MIDI_IN_BYTE_ADDR    equ (ROM4_ADDR + $2304)     ; $FA2304: head byte for Bconin (low 8 bits)
MIDI_IN_ACK_ADDR     equ (ROM4_ADDR + $2308)     ; $FA2308: advance-ack counter — RP bumps it after it pops + republishes

; --- EPIC-09 fast-path OUT stream (commemul, fire-and-forget; must match midi.h) ---
; Each OUT byte is a single ROM3 read whose address encodes the byte:
;   $FB8000 (ROMCMD_START_ADDR + mid-window bias) + MIDI_OUT_MARKER + byte.
; The RP recovers (addr ^ $8000) and routes bit-8 samples to the network — no
; frame, no token, no wait. (bit 9 = MIDI_IN_ADVANCE is added in STORY-02.)
ROM3_SYNC_BASE       equ ($FB0000 + $8000)       ; ROMCMD_START_ADDR + bias (matches send_sync)
MIDI_OUT_MARKER      equ $0100                   ; bit 8: a MIDI OUT byte
ROM3_MIDI_OUT_ADDR   equ (ROM3_SYNC_BASE + MIDI_OUT_MARKER)
MIDI_IN_ADV_MARKER   equ $0200                   ; bit 9: IN consume/advance signal
ROM3_MIDI_IN_ADV_ADDR equ (ROM3_SYNC_BASE + MIDI_IN_ADV_MARKER)
MIDI_DEACT_MARKER    equ $0400                   ; bit 10: warm-reset gate deactivate
ROM3_MIDI_DEACTIVATE_ADDR equ (ROM3_SYNC_BASE + MIDI_DEACT_MARKER)

; --- BIOS install ---
Setexc               equ 5           ; BIOS function 5: Setexc(vecnum, newvec)
VEC_BIOS             equ $2D         ; trap #13 (BIOS) vector number for Setexc
TRAP13_VECTOR        equ $B4         ; trap #13 handler address (read original)

; --- BIOS function numbers (device in the next stack word) ---
Bconstat             equ 1           ; Bconstat(dev) — input status (-1 = char ready)
Bconin               equ 2           ; Bconin(dev)  — read one byte (returns it in d0)
Bconout              equ 3           ; Bconout(dev, ch) — output
MIDI_DEV             equ 3           ; BIOS device 3 = MIDI

; System variable: 0 on a 68000 (short exception frames), non-zero on
; 68010+ (long frames). Used to locate the trap arguments on the stack.
_longframe           equ $59E

; Sync-command helper (defined in main.s, org'd absolute at $FA0000). Called
; through a 32-bit pointer; a cross-module bsr overflows the 16-bit displacement.
    xref send_sync_command_to_sidecart

    section text

; Place this module at its real cartridge address ($FA0800) so absolute
; references to our own labels (XBRA fields, handler entries) resolve to the
; right runtime addresses. main.s does the analogous `org ROM4_ADDR`; the
; linker script (userfw.ld) positions the bytes at file offset 0x800.
    org (ROM4_ADDR + $800)

; ---------------------------------------------------------------------
; USERFW: install the BIOS device-3 hook. Reached via `jsr USERFW` from main.s
; start_rom_code AT BOOT, while send_sync commands still work (the firmware is
; then pure tst.b). CMD_START/launch no longer routes here — main.s rom_function
; boots GEM directly since the hook is already installed.
;
; First fire a one-cycle "deactivate": on a WARM RESET the RP still has the gate
; up from the previous session, which would steal this command frame; the signal
; drops it first. No-op on a cold boot (the RP gate is already down).
; ---------------------------------------------------------------------
userfw:
    movea.l #ROM3_MIDI_DEACTIVATE_ADDR, a0
    tst.b   (a0)                         ; warm-reset: RP drops the gate first
    ; --- install the device-3 hook via Setexc, saving the original vector ---
    move.l  TRAP13_VECTOR.w, d3          ; d3 = original BIOS vector
    move.l  #bios_xbra_old, d4
    bsr     midi_save_vector             ; RP patches *bios_xbra_old = d3
    tst.w   d0
    bne.s   .skip_bios
    move.l  #midi_bios_trap, -(sp)       ; Setexc(VEC_BIOS, midi_bios_trap)
    move.w  #VEC_BIOS, -(sp)
    move.w  #Setexc, -(sp)
    trap    #13
    addq.l  #8, sp
.skip_bios:
    rts

; ---------------------------------------------------------------------
; Patch a ROM longword via the RP (the XBRA <old> field). In: d3 = value,
; d4 = field address. Out: d0 = 0 on success.
; ---------------------------------------------------------------------
midi_save_vector:
    moveq   #8, d1                       ; payload: d3 (value) + d4 (addr)
    move.w  #CMD_MIDI_SAVE_VECTOR, d0
    move.l  #send_sync_command_to_sidecart, a0
    jsr     (a0)
    rts

; ---------------------------------------------------------------------
; BIOS (trap #13) hook, XBRA-wrapped. The hook IS the MIDI device for device 3,
; over the EPIC-09 commemul fast path (no commands, no token wait):
;   Bconstat(3) -> d0 = pre-baked -1/0 status the RP published (char ready?)
;   Bconin(3)   -> read the RP-published head byte, fire a bit-9 advance, wait
;                  for the RP ack, return it in d0
;   Bconout(3)  -> emit the byte as a single bit-8 ROM3 read (emit-only, the
;                  network is the sink) — no chain to the physical Bconout
; Bconstat/Bconin/Bconout are serviced directly (rte) — no Iorec, no ACIA.
; Any other device/function chains to the original BIOS untouched.
; ---------------------------------------------------------------------
    ds.b ((4 - (* & 3)) & 3)             ; 4-byte align (RP writes <old> as a longword)
    dc.l 'XBRA'
    dc.l 'SDMI'                          ; cookie: SidecarTridge MIDI
bios_xbra_old:
    dc.l 0                              ; original trap #13 vector — patched by the RP
midi_bios_trap:
    ; locate the call arguments (md-drives-emulator pattern):
    ; 6(a0) = function, 8(a0) = device, 11(a0) = char low byte
    btst    #5, (sp)                     ; S bit of the saved SR: 0 = user mode
    beq.s   .mbt_user
    move.l  sp, a0
    bra.s   .mbt_cpu
.mbt_user:
    move.l  usp, a0
    subq.l  #6, a0
.mbt_cpu:
    tst.w   _longframe
    beq.s   .mbt_notlong
    addq.w  #2, a0
.mbt_notlong:
    cmp.w   #MIDI_DEV, 8(a0)            ; device 3 (MIDI)?
    beq.s   .mbt_not_chain
    move.l  bios_xbra_old, -(sp)         ; chain to original (XBRA <old> field)
    rts
.mbt_not_chain:
    cmp.w   #Bconout, 6(a0)
    beq.s   .mbt_out
    cmp.w   #Bconin, 6(a0)
    beq.s   .mbt_in
    cmp.w   #Bconstat, 6(a0)
    beq.s   .mbt_stat
    move.l  bios_xbra_old, -(sp)         ; chain to original (XBRA <old> field)
    rts

    ; --- Bconstat(3): char ready? The RP pre-bakes the return (-1 = ready, 0 =
    ; none), so just hand it back. ---
.mbt_stat:
    move.l  MIDI_IN_STATUS_ADDR, d0
    rte

    ; --- Bconin(3): block until a byte, read the RP-published head, fire the
    ; advance, then WAIT for the RP to ack (pop + republish) before returning.
    ; Without the ack the stale MIDI_IN_STATUS lets MIDI Maze re-read the same
    ; byte many times (IN_adv >> RX -> corrupted ring -> "too many machines").
    ; Clobbers d0/d2/a1 (scratch under the BIOS contract), so no spill. ---
.mbt_in:
    move.l  MIDI_IN_STATUS_ADDR, d0     ; spin until the RP flags a byte ready (-1)
    beq.s   .mbt_in
    move.l  MIDI_IN_BYTE_ADDR, d0       ; the pre-published head byte
    and.l   #$ff, d0
    move.l  MIDI_IN_ACK_ADDR, d2        ; snapshot the advance-ack before consuming
    movea.l #ROM3_MIDI_IN_ADV_ADDR, a1  ; bit-9 advance: "head consumed, move on"
    tst.b   (a1)
.mbt_in_ack:
    cmp.l   MIDI_IN_ACK_ADDR, d2        ; block until the RP popped + republished, so
    beq.s   .mbt_in_ack                 ; the next Bconstat/Bconin sees fresh state
    rte

    ; --- Bconout(3): ship the byte (fire-and-forget), then chain to the real
    ; Bconout. One ROM3 read encodes the byte; no command, no token, no wait.
    ; Clobbers only d1/a1 (scratch under the BIOS contract), so no spill. ---
.mbt_out:
    moveq   #0, d1
    move.b  11(a0), d1                  ; d1 = OUT byte (low 8 bits)
    movea.l #ROM3_MIDI_OUT_ADDR, a1     ; ROM3 OUT base ($FB8100)
    tst.b   (a1, d1.w)                  ; emit: address = base + (bit 8 | byte)
    moveq   #0, d0                      ; Bconout return
    rte                                 ; emit-only: network IS the MIDI sink; no
                                        ; chain into the physical ACIA path

; Align the end of the module so the section length stays even — otherwise the
; assembler can leave handler entry points (reached via Setexc / the dispatch)
; on odd addresses, which faults on fetch (3 bombs = address error). Mirrors the
; `even` guard at the end of main.s.
    nop
    nop
    nop
    nop
    even
