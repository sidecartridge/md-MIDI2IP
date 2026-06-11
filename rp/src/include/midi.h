/**
 * File: midi.h
 * Author: Diego Parrilla Santamaría
 * Date: June 2026
 * Copyright: 2026 - GOODDATA LABS SL
 * Description: MIDI-to-IP command handler (RP side).
 */

#ifndef MIDI_H
#define MIDI_H

#include <stddef.h>  // size_t

#include "chandler.h"  // CHANDLER_APP_FREE_OFFSET

// App command namespace for MIDI-to-IP. The high byte selects the app; the
// terminal uses 0x00, so MIDI uses 0x03. Must match APP_MIDI in
// target/atarist/src/userfw.s.
#define APP_MIDI 0x03

// Patch a 32-bit value (the BIOS hook's XBRA <old> vector) into the served ROM
// image. Payload: d3 = value, d4 = address of the field (inside the
// $FA0000-$FAFFFF cartridge window). The m68k handler (userfw.s) chains through
// that field. Must match
// CMD_MIDI_SAVE_VECTOR in userfw.s.
#define CMD_MIDI_SAVE_VECTOR ((APP_MIDI << 8) | 0x00)  // 0x0300

// --- EPIC-02 byte pipe (must match userfw.s) ---
// Dumb, app-agnostic transport: the m68k ships captured MIDI-OUT bytes to the
// RP, and pulls pending MIDI-IN bytes from it. No MIDI semantics live here.
#define CMD_MIDI_SEND ((APP_MIDI << 8) | 0x01)  // 0x0301: m68k -> RP, ship OUT bytes
#define CMD_MIDI_RECV ((APP_MIDI << 8) | 0x02)  // 0x0302: m68k -> RP, request IN bytes

// Shared MIDI-IN fields in the APP_FREE arena ($FA2300), written by the RP and
// read by the m68k (which owns no state in the ROM region). The BIOS hook acts
// as the MIDI device: it reads the depth for Bconstat and pops one byte for
// Bconin (EPIC-08).
#define MIDI_IN_COUNT_OFFSET CHANDLER_APP_FREE_OFFSET         // longword: RP queue depth (Bconstat)
#define MIDI_IN_BUFFER_OFFSET (CHANDLER_APP_FREE_OFFSET + 4)  // longword: one popped byte (Bconin)

// --- Per-app config keys (EPIC-06 STORY-01) — stored in aconfig / CONFIG_FLASH ---
#define MIDI_CFG_HOST "MIDI_HOST"        // string: orchestrator host (IP for now)
#define MIDI_CFG_PORT "MIDI_PORT"        // int: orchestrator TCP port
#define MIDI_CFG_ENABLED "MIDI_ENABLED"  // bool: connect to the orchestrator
#define MIDI_DEFAULT_HOST "0.0.0.0"      // placeholder until set (STORY-04)
#define MIDI_DEFAULT_PORT 5005

// Register the MIDI command handler with chandler and initialise the shared
// IN count to 0. Call once during emul_start(), after chandler_init() and the
// firmware image is copied to RAM.
void midi_init(void);

// EPIC-03: drive the TCP connection to the orchestrator. Call once per main-loop
// iteration (lwIP poll context). No-op until Wi-Fi has an IP.
void midi_net_poll(void);

// EPIC-03 STORY-04: orchestrator link state for display ("up"/"connecting"/"down").
const char *midi_net_status_str(void);

// EPIC-03 STORY-06: format a one-line orchestrator liveness report into buf
// (endpoint, link state, and uptime when connected).
void midi_net_ping(char *buf, size_t len);

#endif  // MIDI_H
