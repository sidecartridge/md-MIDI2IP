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
APP_MIDI             equ $0300
CMD_MIDI_SAVE_VECTOR equ (APP_MIDI + 0)          ; $0300: patch a ROM longword field

; --- EPIC-02 byte pipe (must match rp/src/include/midi.h) ---
; Dumb transport: ship captured OUT bytes to the RP, pull pending IN bytes back.
CMD_MIDI_SEND        equ (APP_MIDI + 1)          ; $0301: m68k -> RP, ship OUT bytes
CMD_MIDI_RECV        equ (APP_MIDI + 2)          ; $0302: m68k -> RP, request IN bytes

; Shared MIDI-IN fields in the APP_FREE arena, written by the RP and read by the
; m68k (which owns no state in the ROM region):
MIDI_IN_COUNT_ADDR   equ (ROM4_ADDR + $2300)     ; $FA2300: pending byte count (RP queue depth)
MIDI_IN_BYTE_ADDR    equ (ROM4_ADDR + $2304)     ; $FA2304: byte popped by CMD_MIDI_RECV (low 8 bits)

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

; Sync-command helper, defined in main.s (org'd absolute at $FA0000). We
; call it through a 32-bit pointer; a plain cross-module `bsr` overflows
; the 16-bit PC-relative displacement.
    xref send_sync_command_to_sidecart

    section text

; Place this module at its real cartridge address ($FA0800) so absolute
; references to our own labels (XBRA fields, handler entries) resolve to the
; right runtime addresses. main.s does the analogous `org ROM4_ADDR`; the
; linker script (userfw.ld) positions the bytes at file offset 0x800.
    org (ROM4_ADDR + $800)

; ---------------------------------------------------------------------
; USERFW entry point. Install the BIOS hook, then return so the cartridge init
; continues booting. MIDI Maze does ALL its MIDI ring traffic through the BIOS
; (Bconstat / Bconin / Bconout, device 3) — not XBIOS — so that is the only hook
; we install.
; ---------------------------------------------------------------------
userfw:
    ; --- BIOS / trap #13 (install via Setexc) ---
    ; The hook IS the MIDI device: it answers Bconstat/Bconin/Bconout (device 3)
    ; directly from the RP, so no Iorec is involved.
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
; d4 = field address. Out: d0 = 0 on success. Clobbers d0-d7 / a0-a3.
; ---------------------------------------------------------------------
midi_save_vector:
    moveq   #8, d1                       ; payload: d3 (value) + d4 (addr)
    move.w  #CMD_MIDI_SAVE_VECTOR, d0
    move.l  #send_sync_command_to_sidecart, a0
    jsr     (a0)
    rts

; ---------------------------------------------------------------------
; BIOS (trap #13) hook, XBRA-wrapped. The hook IS the MIDI device for device 3:
;   Bconstat(3) -> d0 = -1 if the RP has a pending byte (queue depth > 0) else 0
;   Bconin(3)   -> pop one byte from the RP (CMD_MIDI_RECV), return it in d0
;   Bconout(3)  -> ship the byte (CMD_MIDI_SEND), then chain to the real Bconout
; Bconstat/Bconin are serviced directly (set d0, rte) — no Iorec, no chaining.
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
    bne.s   .mbt_chain
    cmp.w   #Bconout, 6(a0)
    beq.s   .mbt_out
    cmp.w   #Bconin, 6(a0)
    beq.s   .mbt_in
    cmp.w   #Bconstat, 6(a0)
    beq.s   .mbt_stat
    bra.s   .mbt_chain                  ; other device-3 function -> chain

    ; --- Bconstat(3): char ready? (read the RP queue depth) ---
.mbt_stat:
    move.l  MIDI_IN_COUNT_ADDR, d0      ; pending byte count
    beq.s   .mbt_rte                    ; 0 -> d0 = 0 (no char)
    moveq   #-1, d0                     ; >0 -> d0 = -1 (char ready)
    bra.s   .mbt_rte

    ; --- Bconin(3): block until a byte, pop it from the RP, return it in d0 ---
.mbt_in:
    move.l  MIDI_IN_COUNT_ADDR, d0      ; spin until the RP has a byte
    beq.s   .mbt_in
    movem.l d3-d7/a3-a6, -(sp)          ; preserve all callee-saved regs (BIOS contract)             ; send_sync clobbers callee-saved regs
    moveq   #0, d1
    move.w  #CMD_MIDI_RECV, d0
    move.l  #send_sync_command_to_sidecart, a0
    jsr     (a0)
    move.l  MIDI_IN_BYTE_ADDR, d0       ; the popped byte
    and.l   #$ff, d0
    movem.l (sp)+, d3-d7/a3-a6
    bra.s   .mbt_rte

    ; --- Bconout(3): ship the byte, then chain to the real Bconout ---
.mbt_out:
    movem.l d3-d7/a3-a6, -(sp)          ; preserve all callee-saved regs (BIOS contract)
    moveq   #0, d3
    move.b  11(a0), d3                  ; d3 = OUT byte (low byte)
    moveq   #4, d1                      ; payload: d3
    move.w  #CMD_MIDI_SEND, d0
    move.l  #send_sync_command_to_sidecart, a0
    jsr     (a0)
    movem.l (sp)+, d3-d7/a3-a6
    ; fall through to chain

.mbt_chain:
    move.l  bios_xbra_old, -(sp)         ; chain to original (XBRA <old> field)
    rts

.mbt_rte:
    rte
