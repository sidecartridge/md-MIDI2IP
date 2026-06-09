; User firmware module — MIDI-to-IP
; (C) 2026 by Diego Parrilla
; License: GPL v3
;
; EPIC-01 (hooks) + a cable-free loopback bring-up.
;
; STORY-01 installs the BIOS (trap #13) and XBIOS (trap #14) vectors using
; the XBRA convention (see below). On top of that this build adds a
; FIRMWARE LOOPBACK so MIDI Maze can run on a single machine with no MIDI
; cable and no second ST: the BIOS Bconout (device 3) hook echoes every
; byte the ST sends into the ST's own MIDI input buffer (Iorec(2)), making
; it a "ring of one". MIDI Maze sends 0x00, reads its own 0x00 back, and
; becomes MASTER — solo-playable against drones. Bconin(3) and the XBIOS
; readback read that same Iorec buffer, so the loopback works whichever
; path MIDI Maze uses to read (this also exercises the open D-05 input
; path). This is the EPIC-01 STORY-05 / EPIC-02 loopback scaffold; the
; network ring later replaces the local echo.
;
; XBRA (eXtended BRanch Administration)
; -------------------------------------
; Each handler is preceded by a 12-byte XBRA header: dc.l 'XBRA', a cookie
; ('SDMI'), and the previous vector (the chain target). The <old> field is
; in cartridge ROM (which the m68k can't write), so the install path hands
; the original vector and the field's address to the RP, which patches the
; field in the served ROM image (rp/src/midi.c). The same mechanism caches
; the MIDI Iorec pointer. Mirrors md-drives-emulator's GEMDRIVE/FLOPPY.

ROM4_ADDR            equ $FA0000

; --- MIDI app command namespace (must match rp/src/include/midi.h) ---
APP_MIDI             equ $0300
CMD_MIDI_SAVE_VECTOR equ (APP_MIDI + 0)          ; $0300: patch a ROM longword field

; --- BIOS / XBIOS install ---
Setexc               equ 5           ; BIOS function 5: Setexc(vecnum, newvec)
Iorec                equ 14          ; XBIOS function 14: Iorec(dev) -> IOREC*
IOREC_MIDI_DEV       equ 2           ; Iorec device 2 = MIDI
VEC_BIOS             equ $2D         ; trap #13 (BIOS) vector number for Setexc
TRAP13_VECTOR        equ $B4         ; trap #13 handler address (read original)
TRAP14_VECTOR        equ $B8         ; trap #14 (XBIOS) handler address (poke)

; --- BIOS function numbers (device in the next stack word) ---
Bconout              equ 3           ; Bconout(dev, ch)
MIDI_DEV             equ 3           ; BIOS device 3 = MIDI

; --- IOREC structure offsets (Atari input record) ---
IOREC_IBUF           equ 0           ; .l buffer pointer
IOREC_IBUFSIZ        equ 4           ; .w buffer size
IOREC_IBUFHD         equ 6           ; .w head index (advanced, then written)
IOREC_IBUFTL         equ 8           ; .w tail index (advanced, then read)

; System variable: 0 on a 68000 (short exception frames), non-zero on
; 68010+ (long frames). Used to locate the trap arguments on the stack.
_longframe           equ $59E

; Sync-command helper, defined in main.s (org'd absolute at $FA0000). We
; call it through a 32-bit pointer; a plain cross-module `bsr` overflows
; the 16-bit PC-relative displacement.
    xref send_sync_command_to_sidecart

    section text

; Place this module at its real cartridge address ($FA0800) so absolute
; references to our own labels (XBRA fields, handler entries, the cached
; Iorec pointer) resolve to the right runtime addresses. main.s does the
; analogous `org ROM4_ADDR`; the linker script (userfw.ld) positions the
; bytes at file offset 0x800.
    org (ROM4_ADDR + $800)

; ---------------------------------------------------------------------
; USERFW entry point. Cache the MIDI Iorec pointer, install the BIOS and
; XBIOS hooks, then return so the cartridge init continues booting.
; ---------------------------------------------------------------------
userfw:
    ; --- cache the MIDI Iorec input-record pointer (for the loopback) ---
    ; Done before installing the XBIOS hook, so Iorec() goes straight to TOS.
    move.w  #IOREC_MIDI_DEV, -(sp)       ; Iorec(2): MIDI input record
    move.w  #Iorec, -(sp)
    trap    #14
    addq.l  #4, sp
    move.l  d0, d3                       ; d3 = IOREC* (MIDI)
    move.l  #midi_iorec_ptr, d4
    bsr     midi_save_vector             ; RP patches *midi_iorec_ptr = d0

    ; --- BIOS / trap #13 (install via Setexc) ---
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

    ; --- XBIOS / trap #14 (direct poke) ---
    move.l  TRAP14_VECTOR.w, d3          ; d3 = original XBIOS vector
    move.l  #xbios_xbra_old, d4
    bsr     midi_save_vector
    tst.w   d0
    bne.s   .skip_xbios
    move.l  #midi_xbios_trap, TRAP14_VECTOR.w
.skip_xbios:

    rts

; ---------------------------------------------------------------------
; Patch a ROM longword via the RP (an XBRA <old> field, or the cached
; Iorec pointer). In: d3 = value, d4 = field address. Out: d0 = 0 on
; success. Clobbers d0-d7 / a0-a3 (per the callee).
; ---------------------------------------------------------------------
midi_save_vector:
    moveq   #8, d1                       ; payload: d3 (value) + d4 (addr)
    move.w  #CMD_MIDI_SAVE_VECTOR, d0
    move.l  #send_sync_command_to_sidecart, a0
    jsr     (a0)
    rts

; Cached MIDI IOREC pointer (patched by the RP at install). 4-byte aligned
; so the RP's longword write is aligned.
    ds.b ((4 - (* & 3)) & 3)
midi_iorec_ptr:
    dc.l 0

; ---------------------------------------------------------------------
; BIOS (trap #13) hook, XBRA-wrapped.
;
; Loopback: on Bconout(device 3) we echo the byte into the MIDI Iorec
; input buffer (write at the head, advance it), so the ST receives its own
; output. We then chain to the original Bconout (which still drives the
; physical port and returns normally). Bconin/Bconstat and the XBIOS
; readback then read the byte from that same Iorec buffer.
; ---------------------------------------------------------------------
    ds.b ((4 - (* & 3)) & 3)             ; 4-byte align (RP writes <old> as a longword)
    dc.l 'XBRA'
    dc.l 'SDMI'                          ; cookie: SidecarTridge MIDI
bios_xbra_old:
    dc.l 0                              ; original trap #13 vector — patched by the RP
midi_bios_trap:
    ; locate the call arguments (md-drives-emulator pattern):
    ; 6(a0) = function, 8(a0) = device, 10(a0) = char word (11(a0) = low byte)
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

    cmp.w   #Bconout, 6(a0)              ; Bconout?
    bne.s   .mbt_chain
    cmp.w   #MIDI_DEV, 8(a0)             ; device 3 (MIDI)?
    bne.s   .mbt_chain

    ; --- echo the byte into the MIDI Iorec input buffer ---
    movem.l d2/a1-a2, -(sp)
    movea.l midi_iorec_ptr, a1          ; a1 = MIDI IOREC*
    move.l  a1, d2
    beq.s   .mbt_inject_done            ; pointer not cached → skip the echo
    movea.l IOREC_IBUF(a1), a2          ; a2 = ibuf
    ; TOS fills the input record by advancing the head FIRST, then storing
    ; at the new head; readers (Bconin / the readback) advance the tail and
    ; read at the new tail. Match that exactly, and drop on overflow.
    move.w  IOREC_IBUFHD(a1), d2        ; d2 = head
    addq.w  #1, d2                       ; head++
    cmp.w   IOREC_IBUFSIZ(a1), d2       ; wrap at end of buffer
    blt.s   .mbt_nowrap
    moveq   #0, d2
.mbt_nowrap:
    cmp.w   IOREC_IBUFTL(a1), d2        ; head caught the tail -> buffer full
    beq.s   .mbt_inject_done            ; full: drop the byte
    move.w  d2, IOREC_IBUFHD(a1)        ; commit the new head
    move.b  11(a0), (a2, d2.w)          ; store the byte at the new head
.mbt_inject_done:
    movem.l (sp)+, d2/a1-a2

.mbt_chain:
    move.l  bios_xbra_old, -(sp)         ; chain to original (XBRA <old> field)
    rts

; ---------------------------------------------------------------------
; XBIOS (trap #14) hook, XBRA-wrapped. Transparent for now — MIDI Maze's
; XBIOS MIDI-IN readback reads the Iorec buffer we populate above, so it
; needs no special handling yet (STORY-04 revisits this).
; ---------------------------------------------------------------------
    ds.b ((4 - (* & 3)) & 3)             ; 4-byte align
    dc.l 'XBRA'
    dc.l 'SDMI'
xbios_xbra_old:
    dc.l 0                              ; original trap #14 vector — patched by the RP
midi_xbios_trap:
    move.l  xbios_xbra_old, -(sp)        ; chain to original (XBRA <old> field)
    rts
