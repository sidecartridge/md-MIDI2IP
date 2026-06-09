/**
 * File: midi.h
 * Author: Diego Parrilla Santamaría
 * Date: June 2026
 * Copyright: 2026 - GOODDATA LABS SL
 * Description: MIDI-to-IP command handler (RP side).
 */

#ifndef MIDI_H
#define MIDI_H

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

// Register the MIDI command handler with chandler. Call once during
// emul_start(), after chandler_init().
void midi_init(void);

#endif  // MIDI_H
