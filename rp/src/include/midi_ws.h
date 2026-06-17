/**
 * File: midi_ws.h
 * Author: Diego Parrilla Santamaría
 * Date: June 2026
 * Copyright: 2026 - GOODDATA LABS SL
 * Description: RFC 6455 client-side WebSocket helpers for MIDI-to-IP (EPIC-13
 * STORY-05). Pure C with no lwIP / pico dependency, so the framing and the
 * handshake math unit-test on the host and interop with the orchestrator's
 * stdlib codec (orchestrator/ws.py). midi.c wires these to the lwIP PCB.
 */
#ifndef MIDI_WS_H
#define MIDI_WS_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

// WebSocket opcodes (RFC 6455 section 5.2).
#define MIDI_WS_OP_CONT 0x0u
#define MIDI_WS_OP_TEXT 0x1u
#define MIDI_WS_OP_BIN 0x2u
#define MIDI_WS_OP_CLOSE 0x8u
#define MIDI_WS_OP_PING 0x9u
#define MIDI_WS_OP_PONG 0xAu

// Header overhead upper bound for a client (masked) frame with a 16-bit length:
// 2 base + 2 length + 4 mask. Size an OUT buffer as payload + this.
#define MIDI_WS_FRAME_OVERHEAD 8

// base64-encode n bytes of `in` into `out` (NUL-terminated). `out` must hold at
// least 4*((n+2)/3)+1 bytes.
void midi_ws_base64(const uint8_t *in, size_t n, char *out);

// Compute Sec-WebSocket-Accept for a client key string (RFC 6455 4.2.2) into
// `out` = base64(sha1(key + GUID)). `out` needs >= 29 bytes.
void midi_ws_accept_key(const char *client_key, char *out);

// Build one final (FIN) masked client frame for `opcode` carrying `payload`
// (`len` <= 65535) into `out`, using mask_key. Returns the total byte count.
// `out` must be at least len + MIDI_WS_FRAME_OVERHEAD bytes.
size_t midi_ws_build_frame(uint8_t *out, uint8_t opcode, const uint8_t *payload,
                           size_t len, const uint8_t mask_key[4]);

// Streaming server->client decoder. Incoming frames are unmasked (RFC 6455:
// only the client masks). Data-frame payloads (binary / continuation) are
// delivered as runs via on_data; a completed control frame (ping/pong/close) is
// delivered via on_ctl with its small payload. A masked frame or an oversize
// control frame is a protocol error: midi_ws_decode returns false and the caller
// resets the link. Frames split across feeds are reassembled.
typedef struct {
  int state;
  uint8_t opcode;
  bool is_control;
  uint64_t remaining;  // payload bytes still to read in the current frame
  uint8_t ext_left;    // extended-length bytes still to read
  uint8_t ctl[125];    // control-frame payload accumulator
  uint8_t ctl_len;
} midi_ws_decoder;

void midi_ws_decoder_init(midi_ws_decoder *d);

bool midi_ws_decode(midi_ws_decoder *d, const uint8_t *data, size_t n,
                    void (*on_data)(const uint8_t *p, size_t len, void *ctx),
                    void (*on_ctl)(uint8_t opcode, const uint8_t *p, size_t len,
                                   void *ctx),
                    void *ctx);

#endif  // MIDI_WS_H
