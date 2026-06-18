/**
 * File: midi.c
 * Author: Diego Parrilla Santamaría
 * Date: June 2026
 * Copyright: 2026 - GOODDATA LABS SL
 * Description: MIDI-to-IP command handler (RP side).
 *
 * EPIC-01 STORY-01: services CMD_MIDI_SAVE_VECTOR. The m68k installs its
 * BIOS (trap #13) hook using the XBRA convention, but the XBRA <old>
 * field lives in the cartridge ROM, which the m68k can't write. So it
 * hands us the original vector and the field's address; we patch the
 * field in the served ROM image so the m68k handler can chain through it.
 * This mirrors how md-drives-emulator saves the GEMDRIVE/FLOPPY vectors.
 */

#include "midi.h"

#include <stdio.h>   // snprintf
#include <stdlib.h>  // atoi
#include <string.h>  // memcmp, strlen (WebSocket handshake)

#include "aconfig.h"  // aconfig_getContext + settings_find_entry
#include "blink.h"
#include "chandler.h"
#include "commemul.h"   // DEBUG: ring instrumentation
#include "constants.h"  // __rom_in_ram_start__
#include "debug.h"
#include "lwip/ip_addr.h"
#include "lwip/tcp.h"
#include "memfunc.h"  // WRITE_AND_SWAP_LONGWORD
#include "midi_ws.h"  // EPIC-13: WebSocket framing + handshake (RFC 6455)
#include "network.h"  // network_getCurrentIp
#include "pico/time.h"
#include "tprotocol.h"  // TransmissionProtocol, TPROTO_* payload macros

// --- EPIC-02 IN queue ---
// Bytes the RP owes the m68k: the network recv pushes here, Bconin pops one at
// a time. Single producer / single consumer, both on the bus loop, so no
// locking. Size is a power of two and must absorb the largest burst the m68k
// hasn't drained yet — MIDI Maze's SEND-DATA (the 64x64 maze + options) is well
// over 4 KB, so the old 1 KB queue dropped bytes; 16 KB gives ample headroom.
#define MIDI_IN_QUEUE_SIZE 16384
static uint8_t midiInQueue[MIDI_IN_QUEUE_SIZE];
static uint16_t midiInHead = 0;  // next write
static uint16_t midiInTail = 0;  // next read
static uint32_t midiInAck =
    0;  // advance-ack: bumped after each pop+republish (Bconin sync)

// --- EPIC-09 OUT queue ---
// MIDI Maze bursts OUT bytes (Bconout) faster than a per-byte tcp_write can
// keep up — under a SEND-DATA burst the TCP send buffer/pbuf pool fills and
// tcp_write returns !=ERR_OK, silently dropping the byte (OUT > RX -> a short
// ring -> "fails to start"). Capture into this ring from the hot path; drain to
// TCP in midi_net_poll (poll context), so bursts are absorbed and nothing is
// lost. Same power-of-two single-producer/single-consumer pattern as IN.
#define MIDI_OUT_QUEUE_SIZE 16384
static uint8_t midiOutQueue[MIDI_OUT_QUEUE_SIZE];
static uint16_t midiOutHead = 0;  // producer (bus loop / hot path)
static uint16_t midiOutTail = 0;  // consumer (net poll)
static uint32_t midiOutDrop = 0;  // DEBUG: ring-full drops (should stay 0)

// --- Time-based staleness cleanup ---
// If pending bytes aren't drained within this window — IN: consumed by the m68k
// (Bconin), OUT: accepted by TCP — the consumer/link has stalled and the pending
// bytes are stale. Flushing them lets a resumed peer resync instead of replaying
// old traffic, which is what produces mid-game glitches. Each *LastDrain stamps
// the last healthy moment (a drain, or an empty->non-empty fill that restarts the
// window); the cleanup flushes a non-empty queue that has had none for STALE_MS.
#define MIDI_QUEUE_STALE_MS 1000
static absolute_time_t midiInLastDrain;
static absolute_time_t midiOutLastDrain;

// DEBUG: fast-path byte counters — printed once/sec as a rate (the MIDI/s trace,
// currently #if 0). midiCmdSend = OUT bytes, midiCmdRecv = IN advances.
static uint32_t midiCmdSend = 0;
static uint32_t midiCmdRecv = 0;
static uint32_t midiNetRx =
    0;  // DEBUG: bytes received from the orchestrator (net -> IN queue)
static volatile bool midiActive = false;  // EPIC-09 fast-path stream gate

// Endpoint config (EPIC-06 STORY-01) — loaded from aconfig in midi_init().
static char midiNetHost[SETTINGS_MAX_VALUE_LENGTH] = MIDI_DEFAULT_HOST;
// The TCP and WebSocket listeners use different ports, so each carrier keeps its
// own; midiNetPort is the active one, picked by the transport (EPIC-13 STORY-06).
static uint16_t midiTcpPort = MIDI_DEFAULT_PORT;    // MIDI_PORT (tcp carrier)
static uint16_t midiWsPort = MIDI_DEFAULT_WS_PORT;  // MIDI_WS_PORT (ws carrier)
static uint16_t midiNetPort = MIDI_DEFAULT_PORT;    // active carrier's port
static bool midiEnabled = true;

// EPIC-13 STORY-05: transport selection. Default TCP (D-13). STORY-06 wires the
// MIDI_TRANSPORT config key + boot-menu toggle to flip this to WebSocket; the WS
// code path below is gated on it, so a TCP install behaves exactly as before.
typedef enum { MIDI_TX_TCP = 0, MIDI_TX_WS } midi_transport_t;
static midi_transport_t midiTransport = MIDI_TX_TCP;
static char midiWsPath[SETTINGS_MAX_VALUE_LENGTH] = MIDI_DEFAULT_WS_PATH;
// EPIC-14 STORY-09: play-room key, sent as Authorization: Bearer on the WS
// handshake (D-14). Empty = the default ring. Normalized to uppercase.
static char midiRoom[SETTINGS_MAX_VALUE_LENGTH] = "";

// WebSocket OUT framing scratch (poll context): one frame at a time, so a single
// static buffer is reused by the OUT drain and the pong responder.
#define MIDI_WS_TX_CHUNK 1024
static uint8_t midiWsTx[MIDI_WS_TX_CHUNK + MIDI_WS_FRAME_OVERHEAD];

static inline bool __not_in_flash_func(midi_in_push)(uint8_t b) {
  uint16_t next = (uint16_t)((midiInHead + 1) & (MIDI_IN_QUEUE_SIZE - 1));
  if (next == midiInTail) return false;  // full: drop
  bool wasEmpty = (midiInHead == midiInTail);
  midiInQueue[midiInHead] = b;
  midiInHead = next;
  // A byte landing in an empty queue restarts the staleness window.
  if (wasEmpty) midiInLastDrain = get_absolute_time();
  return true;
}

// EPIC-09 STORY-02 IN ring: publish the head byte (the next byte Bconin
// returns) and the Bconstat status into the shared region. Byte FIRST, then
// status, so the m68k — which spins on the status before reading the byte —
// never sees a fresh "ready" paired with a stale head byte.
static inline void __not_in_flash_func(midi_in_publish)(void) {
  uint16_t depth =
      (uint16_t)((midiInHead - midiInTail) & (MIDI_IN_QUEUE_SIZE - 1));
  uint8_t head = (depth != 0) ? midiInQueue[midiInTail] : 0;
  WRITE_LONGWORD_RAW((unsigned int)&__rom_in_ram_start__, MIDI_IN_BUFFER_OFFSET,
                     (uint32_t)head * 0x01010101u);
  // Pre-baked Bconstat return: -1 (0xFFFFFFFF) = char ready, 0 = none — so the
  // m68k hook just `move.l`s it into d0 and rte. -1/0 are byte-swap-invariant.
  // Also serves as the Bconin spin flag (non-zero = a byte is ready).
  WRITE_AND_SWAP_LONGWORD((unsigned int)&__rom_in_ram_start__,
                          MIDI_IN_STATUS_OFFSET, depth ? 0xFFFFFFFFu : 0u);
}

// --- EPIC-03 STORY-01: TCP client to the orchestrator ---
// Connection lifecycle. The orchestrator endpoint (host/port) and the enable
// flag come from aconfig (EPIC-06 STORY-01), loaded in midi_init() into
// midiNetHost / midiNetPort / midiEnabled. The RP is a raw-TCP client (lwIP
// NO_SYS poll mode), so everything below runs from the main loop / lwIP poll
// context — no locking.
#define MIDI_NET_BACKOFF_MIN_MS 500   // first reconnect delay
#define MIDI_NET_BACKOFF_MAX_MS 8000  // backoff cap

typedef enum {
  MIDI_NET_DOWN = 0,
  MIDI_NET_CONNECTING,
  MIDI_NET_WS_HANDSHAKE,  // TCP up, GET Upgrade sent, awaiting 101 (WS only)
  MIDI_NET_UP,
} midi_net_state_t;

static midi_net_state_t midiNetState = MIDI_NET_DOWN;
static struct tcp_pcb *midiNetPcb = NULL;
static absolute_time_t midiNetNextAttempt;
static bool midiNetNextAttemptValid = false;
static uint32_t midiNetBackoffMs = MIDI_NET_BACKOFF_MIN_MS;
static bool midiNetLedSteady = false;  // LED currently held steady-on (link up)
static absolute_time_t midiNetUpSince;  // when the current UP session connected

// Discard pending IN bytes. On a link drop they're stale, and the m68k must not
// inject them after a reconnect (STORY-04 defined reset behaviour). Single
// consumer/producer on the bus loop, so the index assignment is atomic enough.
static void midi_net_flush_in_queue(void) {
  midiInTail = midiInHead;
  midi_in_publish();
}

// Defined in the WS block below (needs midiWsDec / midiWsHsLen).
static void midi_ws_reset_rx(void);

// EPIC-15 STORY-01: drop ALL pending bytes (IN and OUT) and reset the WS receive
// state on a link drop, so a reconnect within the stale window cannot replay
// pre-drop traffic. Previously only the IN queue was flushed, leaving queued OUT
// bytes to be sent on the next connection (until the 1 s stale cleanup). Re-stamp
// the staleness timestamps so the cleanup logic stays consistent.
static void midi_net_flush_all(void) {
  midi_net_flush_in_queue();
  midiOutTail = midiOutHead;  // drop queued OUT bytes too
  midiInLastDrain = get_absolute_time();
  midiOutLastDrain = get_absolute_time();
  midi_ws_reset_rx();
}

// Drop the PCB, flush stale IN/OUT bytes + WS state, and go DOWN. Safe from any
// callback.
static void midi_net_reset(void) {
  if (midiNetPcb != NULL) {
    tcp_arg(midiNetPcb, NULL);
    tcp_recv(midiNetPcb, NULL);
    tcp_err(midiNetPcb, NULL);
    tcp_sent(midiNetPcb, NULL);
    if (tcp_close(midiNetPcb) != ERR_OK) {
      tcp_abort(midiNetPcb);
    }
    midiNetPcb = NULL;
  }
  midi_net_flush_all();
  midiNetState = MIDI_NET_DOWN;
}

// --- EPIC-13 STORY-05: WebSocket client (gated by midiTransport == MIDI_TX_WS) ---
// The MIDI byte stream is unchanged (D-02); WebSocket only wraps the carrier
// (D-13). All of this runs in the lwIP poll / callback context (no locking).

// xorshift32 for per-frame mask keys and the client nonce. Masking is an RFC 6455
// requirement for client->server frames; it is not a security feature here, so a
// cheap PRNG seeded from the timer is enough.
static uint32_t midiWsRand = 0;
static uint32_t midi_ws_next_rand(void) {
  uint32_t x = midiWsRand;
  if (x == 0) x = 0x2545F491u ^ time_us_32();
  x ^= x << 13;
  x ^= x >> 17;
  x ^= x << 5;
  midiWsRand = x;
  return x;
}

static void midi_ws_mask_key(uint8_t key[4]) {
  uint32_t r = midi_ws_next_rand();
  key[0] = (uint8_t)r;
  key[1] = (uint8_t)(r >> 8);
  key[2] = (uint8_t)(r >> 16);
  key[3] = (uint8_t)(r >> 24);
}

// WebSocket client runtime state.
static char midiWsKey[32];           // base64 client nonce (24 chars) + NUL
static midi_ws_decoder midiWsDec;    // streaming server->client frame decoder
static uint8_t midiWsHsBuf[512];     // handshake (101) response accumulator
static uint16_t midiWsHsLen = 0;

// EPIC-15 STORY-01: reset the WS receive state so a reconnect starts clean (no
// partial frame or stale handshake bytes carried across a drop).
static void midi_ws_reset_rx(void) {
  midi_ws_decoder_init(&midiWsDec);
  midiWsHsLen = 0;
}

static void midi_net_mark_up(void) {
  midiNetState = MIDI_NET_UP;
  midiNetBackoffMs = MIDI_NET_BACKOFF_MIN_MS;  // reset backoff on success
  midiNetUpSince = get_absolute_time();
}

// Emit one masked client frame (poll/callback context). Used for the OUT drain
// (binary) and the pong responder. Reuses the single midiWsTx scratch buffer.
static void midi_ws_send_frame(uint8_t opcode, const uint8_t *payload,
                               uint16_t len) {
  if (midiNetPcb == NULL) return;
  if (len > MIDI_WS_TX_CHUNK) len = MIDI_WS_TX_CHUNK;  // control payloads are tiny
  uint8_t mask[4];
  midi_ws_mask_key(mask);
  size_t flen = midi_ws_build_frame(midiWsTx, opcode, payload, len, mask);
  if (tcp_write(midiNetPcb, midiWsTx, (u16_t)flen, TCP_WRITE_FLAG_COPY) ==
      ERR_OK) {
    tcp_output(midiNetPcb);
  }
}

// Decoder callbacks. Data frames carry MIDI IN bytes; control frames are tiny.
static void midi_ws_on_data(const uint8_t *p, size_t len, void *ctx) {
  (void)ctx;
  for (size_t i = 0; i < len; i++) {
    midi_in_push(p[i]);
    midiNetRx++;  // DEBUG: orchestrator bytes arrived at the RP
  }
}

static void midi_ws_on_ctl(uint8_t opcode, const uint8_t *p, size_t len,
                           void *ctx) {
  (void)ctx;
  if (opcode == MIDI_WS_OP_PING) {
    midi_ws_send_frame(MIDI_WS_OP_PONG, p, (uint16_t)len);
  } else if (opcode == MIDI_WS_OP_CLOSE) {
    midi_net_reset();  // server asked to close -> drop + reconnect (backoff)
  }
  // MIDI_WS_OP_PONG: nothing to do
}

// Substring search over a non-NUL-terminated byte buffer (the handshake header).
static bool midi_ws_buf_contains(const uint8_t *hay, uint16_t haylen,
                                 const char *needle) {
  uint16_t nlen = (uint16_t)strlen(needle);
  if (nlen == 0 || nlen > haylen) return false;
  for (uint16_t i = 0; (uint16_t)(i + nlen) <= haylen; i++) {
    if (memcmp(hay + i, needle, nlen) == 0) return true;
  }
  return false;
}

// Build and send the RFC 6455 client handshake; go to WS_HANDSHAKE awaiting 101.
static void midi_ws_start_handshake(void) {
  uint8_t nonce[16];
  for (int i = 0; i < 16; i++) nonce[i] = (uint8_t)midi_ws_next_rand();
  midi_ws_base64(nonce, sizeof(nonce), midiWsKey);
  midi_ws_decoder_init(&midiWsDec);
  midiWsHsLen = 0;
  // Room key -> Authorization: Bearer (EPIC-14 STORY-09); empty = the default ring.
  char auth[SETTINGS_MAX_VALUE_LENGTH + 32];
  if (midiRoom[0] != '\0') {
    snprintf(auth, sizeof(auth), "Authorization: Bearer %s\r\n", midiRoom);
  } else {
    auth[0] = '\0';
  }
  char req[512];
  int n = snprintf(req, sizeof(req),
                   "GET %s HTTP/1.1\r\n"
                   "Host: %s:%u\r\n"
                   "Upgrade: websocket\r\n"
                   "Connection: Upgrade\r\n"
                   "Sec-WebSocket-Key: %s\r\n"
                   "%s"
                   "Sec-WebSocket-Version: 13\r\n\r\n",
                   midiWsPath, midiNetHost, (unsigned)midiNetPort, midiWsKey, auth);
  midiNetState = MIDI_NET_WS_HANDSHAKE;
  if (n <= 0 || (size_t)n >= sizeof(req) ||
      tcp_write(midiNetPcb, req, (u16_t)n, TCP_WRITE_FLAG_COPY) != ERR_OK) {
    midi_net_reset();
    return;
  }
  tcp_output(midiNetPcb);
}

// Feed the WS_HANDSHAKE accumulator; once the 101 response is complete, validate
// it (status 101 + the expected Sec-WebSocket-Accept) and go UP, then decode any
// frame bytes that trailed the header. Returns false on a bad/oversize response.
static bool midi_ws_handshake_recv(struct pbuf *p) {
  for (struct pbuf *q = p; q != NULL; q = q->next) {
    const uint8_t *bytes = (const uint8_t *)q->payload;
    for (uint16_t i = 0; i < q->len; i++) {
      if (midiWsHsLen >= sizeof(midiWsHsBuf)) return false;  // header too large
      midiWsHsBuf[midiWsHsLen++] = bytes[i];
    }
  }
  int hdr_end = -1;
  for (uint16_t i = 0; (uint16_t)(i + 4) <= midiWsHsLen; i++) {
    if (midiWsHsBuf[i] == '\r' && midiWsHsBuf[i + 1] == '\n' &&
        midiWsHsBuf[i + 2] == '\r' && midiWsHsBuf[i + 3] == '\n') {
      hdr_end = i + 4;
      break;
    }
  }
  if (hdr_end < 0) return true;  // need more bytes; still waiting
  char expect[32];
  midi_ws_accept_key(midiWsKey, expect);
  if (!midi_ws_buf_contains(midiWsHsBuf, (uint16_t)hdr_end, " 101 ") ||
      !midi_ws_buf_contains(midiWsHsBuf, (uint16_t)hdr_end, expect)) {
    return false;  // not a valid WebSocket upgrade
  }
  midi_net_mark_up();
  DPRINTF("MIDI net: WebSocket upgraded %s:%d%s\n", midiNetHost, midiNetPort,
          midiWsPath);
  // Bytes after the header (if any) are the first WS frames.
  if ((uint16_t)hdr_end < midiWsHsLen) {
    if (!midi_ws_decode(&midiWsDec, midiWsHsBuf + hdr_end,
                        (size_t)(midiWsHsLen - hdr_end), midi_ws_on_data,
                        midi_ws_on_ctl, NULL)) {
      return false;
    }
    midi_in_publish();
  }
  return true;
}

static err_t midi_net_recv_cb(void *arg, struct tcp_pcb *pcb, struct pbuf *p,
                              err_t err) {
  (void)arg;
  if (p == NULL) {  // peer closed the connection
    DPRINTF("MIDI net: peer closed -> down\n");
    midi_net_reset();
    return ERR_OK;
  }
  if (err != ERR_OK) {
    pbuf_free(p);
    return err;
  }

  if (midiTransport == MIDI_TX_WS) {
    if (midiNetState == MIDI_NET_WS_HANDSHAKE) {
      if (!midi_ws_handshake_recv(p)) {
        midi_net_reset();
        pbuf_free(p);
        return ERR_OK;
      }
    } else if (midiNetState == MIDI_NET_UP) {
      // De-frame incoming WS frames into the IN queue (D-02 opaque bytes).
      for (struct pbuf *q = p; q != NULL; q = q->next) {
        if (!midi_ws_decode(&midiWsDec, (const uint8_t *)q->payload, q->len,
                            midi_ws_on_data, midi_ws_on_ctl, NULL)) {
          midi_net_reset();  // protocol error
          pbuf_free(p);
          return ERR_OK;
        }
        if (midiNetState != MIDI_NET_UP) break;  // a close frame reset the link
      }
      if (midiNetState == MIDI_NET_UP) {
        midi_in_publish();  // publish the new head byte + depth for Bconin
      }
    }
    if (midiNetState != MIDI_NET_DOWN && midiNetPcb != NULL) {
      tcp_recved(pcb, p->tot_len);
    }
    pbuf_free(p);
    return ERR_OK;
  }

  // TCP transport: push received bytes into the IN queue; the m68k's Bconin
  // drains the head one byte at a time via the bit-9 advance. Opaque (D-02).
  for (struct pbuf *q = p; q != NULL; q = q->next) {
    const uint8_t *bytes = (const uint8_t *)q->payload;
    for (uint16_t i = 0; i < q->len; i++) {
      midi_in_push(bytes[i]);
      midiNetRx++;  // DEBUG: orchestrator echo arrived at the RP
    }
  }
  midi_in_publish();  // publish the new head byte + depth for Bconin/Bconstat
  tcp_recved(pcb, p->tot_len);
  pbuf_free(p);
  return ERR_OK;
}

static void midi_net_err_cb(void *arg, err_t err) {
  (void)arg;
  // lwIP has already freed the PCB on error.
  midiNetPcb = NULL;
  midi_net_flush_all();  // EPIC-15: drop IN + OUT + WS state on the error drop too
  midiNetState = MIDI_NET_DOWN;
  DPRINTF("MIDI net: error %d -> down\n", err);
}

static err_t midi_net_connected_cb(void *arg, struct tcp_pcb *pcb, err_t err) {
  (void)arg;
  (void)pcb;
  if (err != ERR_OK) {
    midi_net_reset();
    return err;
  }
  if (midiTransport == MIDI_TX_WS) {
    // TCP is up; the link is not UP until the WebSocket 101 handshake completes.
    midi_ws_start_handshake();
    DPRINTF("MIDI net: TCP up, WebSocket handshake to %s:%d%s\n", midiNetHost,
            midiNetPort, midiWsPath);
    return ERR_OK;
  }
  midi_net_mark_up();
  DPRINTF("MIDI net: connected to %s:%d\n", midiNetHost, midiNetPort);
  return ERR_OK;
}

static void midi_net_try_connect(void) {
  ip_addr_t ip;
  if (!ipaddr_aton(midiNetHost, &ip)) {
    return;
  }
  midiNetPcb = tcp_new();
  if (midiNetPcb == NULL) {
    return;
  }
  tcp_nagle_disable(
      midiNetPcb);  // TCP_NODELAY — MIDI is latency-sensitive (D-03/C-01)
  tcp_arg(midiNetPcb, NULL);
  tcp_recv(midiNetPcb, midi_net_recv_cb);
  tcp_err(midiNetPcb, midi_net_err_cb);
  midiNetState = MIDI_NET_CONNECTING;
  if (tcp_connect(midiNetPcb, &ip, midiNetPort, midi_net_connected_cb) !=
      ERR_OK) {
    midi_net_reset();
  }
}

// STORY-02: send one OUT byte to the orchestrator. Dropped if the link is down
// (gameplay needs the peer up; STORY-04 surfaces link state). tcp_output
// flushes immediately — TCP_NODELAY, MIDI is latency-sensitive (C-01).
static void __not_in_flash_func(midi_net_send_byte)(uint8_t b) {
  // Hot path (bus loop): just enqueue. The drain to TCP happens in the poll
  // context (midi_net_flush_out) so a full send buffer retries instead of
  // dropping. Drop here only if the (large) ring is genuinely full.
  uint16_t next = (uint16_t)((midiOutHead + 1) & (MIDI_OUT_QUEUE_SIZE - 1));
  if (next == midiOutTail) {
    midiOutDrop++;
    return;
  }
  bool wasEmpty = (midiOutHead == midiOutTail);
  midiOutQueue[midiOutHead] = b;
  midiOutHead = next;
  if (wasEmpty) midiOutLastDrain = get_absolute_time();
}

// Drain queued OUT bytes to the orchestrator. Poll context only. Writes in
// contiguous runs up to the current TCP send window; if the buffer is full it
// stops and the bytes wait in the ring for the next poll (no loss). One
// tcp_output per drain coalesces the burst into proper segments.
static void midi_net_flush_out(void) {
  if (midiNetState != MIDI_NET_UP || midiNetPcb == NULL) {
    return;
  }
  bool wrote = false;
  while (midiOutTail != midiOutHead) {
    uint16_t sndbuf = tcp_sndbuf(midiNetPcb);
    if (sndbuf == 0) break;  // send buffer full — retry next poll
    uint16_t contig = (midiOutHead > midiOutTail)
                          ? (uint16_t)(midiOutHead - midiOutTail)
                          : (uint16_t)(MIDI_OUT_QUEUE_SIZE - midiOutTail);
    if (midiTransport == MIDI_TX_WS) {
      // Wrap a contiguous run in one masked binary frame; leave room in the send
      // window for the frame header + mask. Multiple frames per drain are fine,
      // the receiver concatenates the payloads (D-02 order preserved).
      if (sndbuf <= MIDI_WS_FRAME_OVERHEAD) break;  // no room for a frame yet
      uint16_t maxpay = (uint16_t)(sndbuf - MIDI_WS_FRAME_OVERHEAD);
      if (maxpay > MIDI_WS_TX_CHUNK) maxpay = MIDI_WS_TX_CHUNK;
      uint16_t n = (contig < maxpay) ? contig : maxpay;
      uint8_t mask[4];
      midi_ws_mask_key(mask);
      size_t flen = midi_ws_build_frame(midiWsTx, MIDI_WS_OP_BIN,
                                        &midiOutQueue[midiOutTail], n, mask);
      if (tcp_write(midiNetPcb, midiWsTx, (u16_t)flen, TCP_WRITE_FLAG_COPY) !=
          ERR_OK) {
        break;  // couldn't enqueue — retry next poll
      }
      midiOutTail = (uint16_t)((midiOutTail + n) & (MIDI_OUT_QUEUE_SIZE - 1));
      wrote = true;
    } else {
      uint16_t n = (contig < sndbuf) ? contig : sndbuf;
      if (tcp_write(midiNetPcb, &midiOutQueue[midiOutTail], n,
                    TCP_WRITE_FLAG_COPY) != ERR_OK) {
        break;  // couldn't enqueue — retry next poll
      }
      midiOutTail = (uint16_t)((midiOutTail + n) & (MIDI_OUT_QUEUE_SIZE - 1));
      wrote = true;
    }
  }
  if (wrote) {
    tcp_output(midiNetPcb);
    midiOutLastDrain = get_absolute_time();  // TCP is accepting — healthy
  }
}

// Drop pending bytes whose consumer/link has stalled past MIDI_QUEUE_STALE_MS —
// they're stale and replaying them desyncs the ring. Poll context only.
static void midi_queue_cleanup(void) {
  absolute_time_t now = get_absolute_time();
  if (midiInHead != midiInTail &&
      absolute_time_diff_us(midiInLastDrain, now) > MIDI_QUEUE_STALE_MS * 1000) {
    uint16_t dropped =
        (uint16_t)((midiInHead - midiInTail) & (MIDI_IN_QUEUE_SIZE - 1));
    midiInTail = midiInHead;
    midi_in_publish();  // Bconstat now reports "no byte"
    midiInLastDrain = now;
    DPRINTF("MIDI IN stale: flushed %u byte(s)\n", dropped);
  }
  if (midiOutHead != midiOutTail &&
      absolute_time_diff_us(midiOutLastDrain, now) >
          MIDI_QUEUE_STALE_MS * 1000) {
    uint16_t dropped =
        (uint16_t)((midiOutHead - midiOutTail) & (MIDI_OUT_QUEUE_SIZE - 1));
    midiOutTail = midiOutHead;
    midiOutLastDrain = now;
    DPRINTF("MIDI OUT stale: flushed %u byte(s)\n", dropped);
  }
}

// STORY-04: the on-board green LED mirrors the orchestrator link — steady on
// when connected, blinking while down/connecting. blink_toogle()
// self-rate-limits at CHARACTER_GAP_MS, and blink_on() is called once per UP
// transition (it talks to the CYW43 over SPI, so we don't hammer it every
// tick).
static void midi_net_update_led(void) {
  if (midiNetState == MIDI_NET_UP) {
    if (!midiNetLedSteady) {
      blink_on();
      midiNetLedSteady = true;
    }
    return;
  }
  midiNetLedSteady = false;
  blink_toogle();
}

// Drive the connection. Call once per main-loop iteration (poll context). When
// down, reconnects with exponential backoff (MIN..MAX) once Wi-Fi has an IP;
// the backoff resets on a successful connect.
void midi_net_poll(void) {
  midi_net_update_led();
  midi_net_flush_out();   // drain queued OUT bytes to the orchestrator
  midi_queue_cleanup();   // drop stale pending bytes if a side has stalled
#if 0  // per-second MIDI/s rate trace — re-enable to instrument throughput
  static absolute_time_t cmdStatAt = {0};
  static uint32_t lastSend = 0, lastRecv = 0, lastRx = 0, lastSamples = 0;
  if (absolute_time_diff_us(get_absolute_time(), cmdStatAt) <= 0) {
    uint32_t samples = commemul_samplesWritten();
    DPRINTF(
        "MIDI/s: OUT=%lu RX=%lu IN_adv=%lu active=%d cap/s=%lu ringdepth=%lu "
        "outdrop=%lu\n",
        (unsigned long)(midiCmdSend - lastSend),
        (unsigned long)(midiNetRx - lastRx),
        (unsigned long)(midiCmdRecv - lastRecv), (int)midiActive,
        (unsigned long)(samples - lastSamples),
        (unsigned long)commemul_ringDepth(), (unsigned long)midiOutDrop);
    lastSend = midiCmdSend;
    lastRecv = midiCmdRecv;
    lastRx = midiNetRx;
    lastSamples = samples;
    cmdStatAt = make_timeout_time_ms(1000);
  }
#endif
  if (!midiEnabled) {
    return;  // STORY-01: orchestrator connection disabled in config
  }
  if (midiNetState != MIDI_NET_DOWN) {
    return;
  }
  ip_addr_t myip = network_getCurrentIp();
  if (ip_addr_isany_val(myip)) {
    return;  // Wi-Fi not up yet
  }
  absolute_time_t now = get_absolute_time();
  if (midiNetNextAttemptValid &&
      absolute_time_diff_us(now, midiNetNextAttempt) > 0) {
    return;  // waiting for the backoff interval
  }
  midiNetNextAttemptValid = true;
  midiNetNextAttempt = make_timeout_time_ms(midiNetBackoffMs);
  // Grow the backoff for the next attempt (reset to MIN on a successful
  // connect).
  uint32_t next = midiNetBackoffMs * 2;
  midiNetBackoffMs =
      (next > MIDI_NET_BACKOFF_MAX_MS) ? MIDI_NET_BACKOFF_MAX_MS : next;
  midi_net_try_connect();
}

// STORY-04: link state for the terminal status screen.
const char *midi_net_status_str(void) {
  switch (midiNetState) {
    case MIDI_NET_UP:
      return "up";
    case MIDI_NET_CONNECTING:
    case MIDI_NET_WS_HANDSHAKE:
      return "connecting";
    default:
      return "down";
  }
}

// EPIC-13 STORY-06: the active transport for the menu/status display.
const char *midi_net_transport_str(void) {
  return (midiTransport == MIDI_TX_WS) ? "ws" : "tcp";
}

// EPIC-13: the aconfig port key for the active transport, so the menu shows and
// edits the port that matches the selected carrier.
const char *midi_net_port_key(void) {
  return (midiTransport == MIDI_TX_WS) ? MIDI_CFG_WS_PORT : MIDI_CFG_PORT;
}

// EPIC-14 STORY-09: the configured room key for the menu/status ("" = default ring).
const char *midi_net_room_str(void) { return midiRoom; }

// STORY-06: format a one-line orchestrator liveness report — endpoint, link
// state, and (when up) how long the session has been connected. Reuses the
// persistent connection; no extra probe traffic.
void midi_net_ping(char *buf, size_t len) {
  if (midiNetState == MIDI_NET_UP) {
    uint32_t up_s =
        (uint32_t)(absolute_time_diff_us(midiNetUpSince, get_absolute_time()) /
                   1000000);
    snprintf(buf, len, "%s:%d [%s] up (%lus)", midiNetHost, midiNetPort,
             midi_net_transport_str(), (unsigned long)up_s);
  } else {
    snprintf(buf, len, "%s:%d [%s] %s", midiNetHost, midiNetPort,
             midi_net_transport_str(), midi_net_status_str());
  }
}

// Called from chandler_loop for every parsed command (kept in RAM — hot
// path). chandler has already advanced payloadPtr past the random token,
// so payloadPtr points at the first parameter (d3).
// EPIC-09 fast-path: once the firmware is live, MIDI OUT bytes arrive as raw
// commemul samples (one ROM3 read per byte) instead of CMD_MIDI_SEND frames.
// midiActive gates the routing so the boot-menu/config command frames still
// reach the TPROTOCOL parser (their payload words can have bit 8 set too).
// Committed RP-side at firmware launch (cmdFirmware), like md-devops's
// emul_enterFirmwareMode — set BEFORE the ST starts emitting MIDI, with no
// dependency on a round-trip command.
void midi_set_active(bool active) { midiActive = active; }

static bool __not_in_flash_func(midi_rom3_consumer)(uint16_t addr_lsb) {
  if (!midiActive) {
    return false;  // config phase — let TPROTOCOL parse the sample
  }
  if (addr_lsb & MIDI_DEACTIVATE) {  // bit 10: ST warm-reset — drop the gate so
    midiActive = false;              // the re-install's command frame works
    return true;
  }
  if (addr_lsb & MIDI_IN_ADVANCE) {  // bit 9: IN consume — pop the ring head
    if (midiInTail != midiInHead) {
      midiInTail = (uint16_t)((midiInTail + 1) & (MIDI_IN_QUEUE_SIZE - 1));
    }
    midiInLastDrain = get_absolute_time();  // the m68k is consuming — healthy
    midi_in_publish();  // republish the new head byte + status
    // Ack the advance: the m68k's Bconin blocks on this until we've popped +
    // republished, so a stale MIDI_IN_STATUS can't be re-read (IN_adv >> RX).
    midiInAck++;
    WRITE_AND_SWAP_LONGWORD((unsigned int)&__rom_in_ram_start__,
                            MIDI_IN_ACK_OFFSET, midiInAck);
    midiCmdRecv++;  // DEBUG: IN advances/s
    return true;
  }
  if (addr_lsb & MIDI_OUT_MARKER) {  // bit 8: a fire-and-forget OUT byte
    midi_net_send_byte((uint8_t)(addr_lsb & 0xFFu));
    midiCmdSend++;  // DEBUG: OUT bytes/s
    return true;
  }
  return false;
}

static void __not_in_flash_func(midi_command_cb)(TransmissionProtocol *protocol,
                                                 uint16_t *payloadPtr) {
  // Only handle commands in the MIDI app namespace; the terminal commands
  // and anything else are for other callbacks.
  if (((protocol->command_id >> 8) & 0xFF) != APP_MIDI) {
    return;
  }

  switch (protocol->command_id) {
    case CMD_MIDI_SAVE_VECTOR: {
      uint32_t oldVector = TPROTO_GET_PAYLOAD_PARAM32(payloadPtr);  // d3
      uint32_t xbraFieldAddr =
          TPROTO_GET_NEXT32_PAYLOAD_PARAM32(payloadPtr);  // d4

      // The XBRA <old> field is a cartridge address ($FA0000-$FAFFFF); its
      // low 16 bits are the offset into the served ROM mirror. The m68k
      // aligns the field to 4 bytes, so this longword write is aligned.
      uint32_t offset = xbraFieldAddr & 0xFFFFu;
      WRITE_AND_SWAP_LONGWORD((unsigned int)&__rom_in_ram_start__, offset,
                              oldVector);
      DPRINTF("MIDI: saved value %08X into ROM field offset %04X\n", oldVector,
              offset);
      // This runs at BOOT now (main.s install_midi_hook), while the config menu
      // still needs the command channel — so do NOT gate or tear down here.
      // midiActive + chandler_clearCB happen at firmware launch (cmdFirmware).
      break;
    }
    default:
      DPRINTF("MIDI: unknown command %04X\n", protocol->command_id);
      break;
  }
}

// Load the orchestrator endpoint config (MIDI_HOST/PORT/ENABLED) from aconfig
// into the runtime variables. aconfig_init() ran in main() before this.
static void midi_load_config(void) {
  SettingsContext *cfg = aconfig_getContext();
  if (cfg != NULL) {
    SettingsConfigEntry *e = settings_find_entry(cfg, MIDI_CFG_HOST);
    if (e != NULL && e->value[0] != '\0') {
      snprintf(midiNetHost, sizeof(midiNetHost), "%s", e->value);
    }
    e = settings_find_entry(cfg, MIDI_CFG_PORT);
    if (e != NULL && e->value[0] != '\0') {
      midiTcpPort = (uint16_t)atoi(e->value);
    }
    e = settings_find_entry(cfg, MIDI_CFG_WS_PORT);
    if (e != NULL && e->value[0] != '\0') {
      midiWsPort = (uint16_t)atoi(e->value);
    }
    e = settings_find_entry(cfg, MIDI_CFG_ENABLED);
    if (e != NULL && e->value[0] != '\0') {
      char c = e->value[0];
      midiEnabled = (c == 't' || c == 'T' || c == '1' || c == 'y' || c == 'Y');
    }
    e = settings_find_entry(cfg, MIDI_CFG_TRANSPORT);
    if (e != NULL && e->value[0] != '\0') {
      char c = e->value[0];
      midiTransport = (c == 'w' || c == 'W') ? MIDI_TX_WS : MIDI_TX_TCP;
    }
    e = settings_find_entry(cfg, MIDI_CFG_WS_PATH);
    if (e != NULL && e->value[0] != '\0') {
      snprintf(midiWsPath, sizeof(midiWsPath), "%s", e->value);
    }
    e = settings_find_entry(cfg, MIDI_CFG_ROOM);
    midiRoom[0] = '\0';
    if (e != NULL && e->value[0] != '\0') {
      snprintf(midiRoom, sizeof(midiRoom), "%s", e->value);
      for (char *q = midiRoom; *q != '\0'; q++) {  // normalize to uppercase (D-14)
        if (*q >= 'a' && *q <= 'z') *q = (char)(*q - 32);
      }
    }
  }
  // The active carrier's port follows the transport selection (EPIC-13 STORY-06).
  midiNetPort = (midiTransport == MIDI_TX_WS) ? midiWsPort : midiTcpPort;
  DPRINTF(
      "MIDI cfg: host=%s tcp=%u ws=%u active=%u enabled=%d transport=%s path=%s\n",
      midiNetHost, (unsigned)midiTcpPort, (unsigned)midiWsPort,
      (unsigned)midiNetPort, (int)midiEnabled, midi_net_transport_str(),
      midiWsPath);
}

// EPIC-06 STORY-04: re-read the endpoint config and restart the connection so a
// host/port change applies live — drop any current connection and reconnect to
// the new endpoint promptly (no backoff wait).
void midi_net_reload(void) {
  midi_load_config();
  midi_net_reset();  // close any live pcb -> MIDI_NET_DOWN, flush the IN queue
  midiNetBackoffMs = MIDI_NET_BACKOFF_MIN_MS;
  midiNetNextAttemptValid =
      false;  // let midi_net_poll connect on the next tick
}

void midi_init(void) {
  // Load the orchestrator endpoint config (EPIC-06 STORY-01). aconfig_init()
  // ran in main() before emul_start(), so the context is populated.
  midi_load_config();

  // No byte ready at boot (Bconstat status = 0). The RP owns these fields in
  // the served ROM image; the m68k only ever reads them.
  WRITE_AND_SWAP_LONGWORD((unsigned int)&__rom_in_ram_start__,
                          MIDI_IN_STATUS_OFFSET, 0);
  WRITE_AND_SWAP_LONGWORD((unsigned int)&__rom_in_ram_start__,
                          MIDI_IN_ACK_OFFSET, 0);
  midiInLastDrain = get_absolute_time();
  midiOutLastDrain = get_absolute_time();
  chandler_addCB(midi_command_cb);
  chandler_setRawConsumer(midi_rom3_consumer);  // EPIC-09 fast-path OUT stream
}
