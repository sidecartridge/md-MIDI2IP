/**
 * File: midi.h
 * Author: Diego Parrilla Santamaría
 * Date: June 2026
 * Copyright: 2026 - GOODDATA LABS SL
 * Description: MIDI-to-IP command handler (RP side).
 */

#ifndef MIDI_H
#define MIDI_H

#include "chandler.h"  // CHANDLER_APP_FREE_OFFSET

// App command namespace for MIDI-to-IP. The high byte selects the app; the
// terminal uses 0x00, so MIDI uses 0x03. Must match APP_MIDI in
// target/atarist/src/userfw.s.
#define APP_MIDI 0x03

// Patch a 32-bit value (an XBRA <old> vector, or the cached MIDI Iorec
// pointer) into the served ROM image. Payload: d3 = value, d4 = address of
// the field (inside the $FA0000-$FAFFFF cartridge window). The m68k handler
// (userfw.s) chains through / reads that field. Must match
// CMD_MIDI_SAVE_VECTOR in userfw.s.
#define CMD_MIDI_SAVE_VECTOR ((APP_MIDI << 8) | 0x00)  // 0x0300

// --- EPIC-02 byte pipe (must match userfw.s) ---
// Dumb, app-agnostic transport: the m68k ships captured MIDI-OUT bytes to the
// RP, and pulls pending MIDI-IN bytes from it. No MIDI semantics live here.
#define CMD_MIDI_SEND ((APP_MIDI << 8) | 0x01)  // 0x0301: m68k -> RP, ship OUT bytes
#define CMD_MIDI_RECV ((APP_MIDI << 8) | 0x02)  // 0x0302: m68k -> RP, request IN bytes

// Shared MIDI-IN buffer in the APP_FREE arena ($FA2300). The RP writes the
// count and bytes here on CMD_MIDI_RECV; the m68k only reads them (it owns no
// state in the ROM region). Modeled on GEMDRIVE's READ_BYTES / READ_BUFFER.
#define MIDI_IN_BUFFER_SIZE 256
#define MIDI_IN_COUNT_OFFSET CHANDLER_APP_FREE_OFFSET         // longword: pending byte count
#define MIDI_IN_BUFFER_OFFSET (CHANDLER_APP_FREE_OFFSET + 4)  // the bytes

// Register the MIDI command handler with chandler and initialise the shared
// IN count to 0. Call once during emul_start(), after chandler_init() and the
// firmware image is copied to RAM.
void midi_init(void);

#endif  // MIDI_H
