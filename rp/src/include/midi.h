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

// The EPIC-02 per-byte CMD_MIDI_SEND/RECV commands are retired — OUT/IN now ride
// the commemul fast path (EPIC-09 STORY-03). Save-vector is the only MIDI command.

// --- EPIC-09 fast-path stream markers (commemul samples, post-XOR; must match
// userfw.s). The OUT byte streams to the RP as a single ROM3 read; the RP routes
// it before the TPROTOCOL parser. Gated by midiActive (midi.c) so they never
// collide with a live command frame's payload words during config.
#define MIDI_OUT_MARKER 0x0100u  // bit 8: a MIDI OUT byte (ST->RP); low 8 = byte
#define MIDI_IN_ADVANCE 0x0200u  // bit 9: IN consume signal (STORY-02)
#define MIDI_DEACTIVATE 0x0400u  // bit 10: ST re-booted — drop the gate so the
                                 // re-install's command frame works (warm reset)

// Shared MIDI-IN fields in the APP_FREE arena ($FA2300), written by the RP and
// read by the m68k (which owns no state in the ROM region). The BIOS hook acts
// as the MIDI device: it reads the depth for Bconstat and pops one byte for
// Bconin (EPIC-08).
#define MIDI_IN_STATUS_OFFSET CHANDLER_APP_FREE_OFFSET        // longword: pre-baked Bconstat return, -1 = char ready / 0 = none (also the Bconin spin flag)
#define MIDI_IN_BUFFER_OFFSET (CHANDLER_APP_FREE_OFFSET + 4)  // longword: one popped byte (Bconin)
#define MIDI_IN_ACK_OFFSET (CHANDLER_APP_FREE_OFFSET + 8)     // longword: advance-ack; RP bumps it after a pop+republish so Bconin can block until consumed

// --- Per-app config keys (EPIC-06 STORY-01) — stored in aconfig / CONFIG_FLASH ---
#define MIDI_CFG_HOST "MIDI_HOST"        // string: orchestrator host (IP for now)
#define MIDI_CFG_PORT "MIDI_PORT"        // int: orchestrator TCP port
#define MIDI_CFG_ENABLED "MIDI_ENABLED"  // bool: connect to the orchestrator
#define MIDI_CFG_TRANSPORT "MIDI_TRANSPORT"  // string: "tcp" | "ws" (EPIC-13 D-13)
#define MIDI_CFG_WS_PORT "MIDI_WS_PORT"      // int: orchestrator WebSocket port
#define MIDI_CFG_WS_PATH "MIDI_WS_PATH"      // string: WebSocket request path
#define MIDI_DEFAULT_HOST "0.0.0.0"      // placeholder until set (STORY-04)
#define MIDI_DEFAULT_PORT 5005           // TCP carrier (orchestrator --port)
#define MIDI_DEFAULT_TRANSPORT "tcp"     // EPIC-13: default carrier (D-13)
#define MIDI_DEFAULT_WS_PORT 5006        // WebSocket carrier (orchestrator --ws-port)
#define MIDI_DEFAULT_WS_PATH "/"         // EPIC-13: WebSocket request path

// Register the MIDI command handler with chandler and initialise the shared
// IN count to 0. Call once during emul_start(), after chandler_init() and the
// firmware image is copied to RAM.
void midi_init(void);

// EPIC-03: drive the TCP connection to the orchestrator. Call once per main-loop
// iteration (lwIP poll context). No-op until Wi-Fi has an IP.
void midi_net_poll(void);

// EPIC-06 STORY-04: re-read the endpoint config (host/port/enabled) and restart
// the connection so an edit applies live (drop + reconnect to the new endpoint).
void midi_net_reload(void);

// Commit the fast-path MIDI stream (EPIC-09). Called RP-side at firmware launch,
// before the ST begins emitting MIDI — see cmdFirmware / md-devops firmware mode.
void midi_set_active(bool active);

// EPIC-03 STORY-04: orchestrator link state for display ("up"/"connecting"/"down").
const char *midi_net_status_str(void);

// EPIC-13 STORY-06: the active transport for display ("tcp"/"ws").
const char *midi_net_transport_str(void);

// EPIC-13: the aconfig port key for the active transport (MIDI_PORT for tcp,
// MIDI_WS_PORT for ws), so the menu shows/edits the right one.
const char *midi_net_port_key(void);

// EPIC-03 STORY-06: format a one-line orchestrator liveness report into buf
// (endpoint, link state, and uptime when connected).
void midi_net_ping(char *buf, size_t len);

#endif  // MIDI_H
