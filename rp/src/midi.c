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

#include "aconfig.h"  // aconfig_getContext + settings_find_entry
#include "blink.h"
#include "chandler.h"
#include "constants.h"  // __rom_in_ram_start__
#include "debug.h"
#include "lwip/ip_addr.h"
#include "lwip/tcp.h"
#include "memfunc.h"  // WRITE_AND_SWAP_LONGWORD
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

// DEBUG: command counters — printed once/sec as a rate (commands/s = inverse of
// per-byte latency) to measure CMD_MIDI_SEND / CMD_MIDI_RECV throughput.
static uint32_t midiCmdSend = 0;
static uint32_t midiCmdRecv = 0;

// Endpoint config (EPIC-06 STORY-01) — loaded from aconfig in midi_init().
static char midiNetHost[SETTINGS_MAX_VALUE_LENGTH] = MIDI_DEFAULT_HOST;
static uint16_t midiNetPort = MIDI_DEFAULT_PORT;
static bool midiEnabled = true;

static inline void __not_in_flash_func(midi_in_push)(uint8_t b) {
  uint16_t next = (uint16_t)((midiInHead + 1) & (MIDI_IN_QUEUE_SIZE - 1));
  if (next == midiInTail) return;  // full: drop
  midiInQueue[midiInHead] = b;
  midiInHead = next;
}

// Publish the IN-queue depth to the shared region so the m68k's Bconstat(3)
// can read it without a command (the hook IS the MIDI device — EPIC-08).
static inline void __not_in_flash_func(midi_publish_depth)(void) {
  uint16_t depth = (uint16_t)((midiInHead - midiInTail) & (MIDI_IN_QUEUE_SIZE - 1));
  WRITE_AND_SWAP_LONGWORD((unsigned int)&__rom_in_ram_start__, MIDI_IN_COUNT_OFFSET,
                          depth);
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
  midi_publish_depth();
}

// Drop the PCB, flush stale IN bytes, and go DOWN. Safe from any callback.
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
  midi_net_flush_in_queue();
  midiNetState = MIDI_NET_DOWN;
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
  // STORY-03: push received bytes into the IN queue; CMD_MIDI_RECV drains it
  // into the shared buffer for the m68k. Opaque bytes (D-02) — no parsing.
  for (struct pbuf *q = p; q != NULL; q = q->next) {
    const uint8_t *bytes = (const uint8_t *)q->payload;
    for (uint16_t i = 0; i < q->len; i++) {
      midi_in_push(bytes[i]);
    }
  }
  midi_publish_depth();  // let the m68k's Bconstat see the new bytes
  tcp_recved(pcb, p->tot_len);
  pbuf_free(p);
  return ERR_OK;
}

static void midi_net_err_cb(void *arg, err_t err) {
  (void)arg;
  // lwIP has already freed the PCB on error.
  midiNetPcb = NULL;
  midi_net_flush_in_queue();
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
  midiNetState = MIDI_NET_UP;
  midiNetBackoffMs = MIDI_NET_BACKOFF_MIN_MS;  // reset backoff on success
  midiNetUpSince = get_absolute_time();
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
static void midi_net_send_byte(uint8_t b) {
  if (midiNetState != MIDI_NET_UP || midiNetPcb == NULL) {
    return;
  }
  if (tcp_write(midiNetPcb, &b, 1, TCP_WRITE_FLAG_COPY) == ERR_OK) {
    tcp_output(midiNetPcb);
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
  // DEBUG: once/sec, print the command rate (= bytes/sec each way).
  static absolute_time_t cmdStatAt = {0};
  static uint32_t lastSend = 0, lastRecv = 0;
  if (absolute_time_diff_us(get_absolute_time(), cmdStatAt) <= 0) {
    DPRINTF("MIDI cmd/s: SEND=%lu RECV=%lu\n",
            (unsigned long)(midiCmdSend - lastSend),
            (unsigned long)(midiCmdRecv - lastRecv));
    lastSend = midiCmdSend;
    lastRecv = midiCmdRecv;
    cmdStatAt = make_timeout_time_ms(1000);
  }
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
      return "connecting";
    default:
      return "down";
  }
}

// STORY-06: format a one-line orchestrator liveness report — endpoint, link
// state, and (when up) how long the session has been connected. Reuses the
// persistent connection; no extra probe traffic.
void midi_net_ping(char *buf, size_t len) {
  if (midiNetState == MIDI_NET_UP) {
    uint32_t up_s =
        (uint32_t)(absolute_time_diff_us(midiNetUpSince, get_absolute_time()) /
                   1000000);
    snprintf(buf, len, "%s:%d up (%lus)", midiNetHost, midiNetPort,
             (unsigned long)up_s);
  } else {
    snprintf(buf, len, "%s:%d %s", midiNetHost, midiNetPort,
             midi_net_status_str());
  }
}

// Called from chandler_loop for every parsed command (kept in RAM — hot
// path). chandler has already advanced payloadPtr past the random token,
// so payloadPtr points at the first parameter (d3).
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
      break;
    }
    case CMD_MIDI_SEND: {
      // m68k shipped an OUT byte — send it to the orchestrator. (Was the
      // EPIC-02 local echo; the echo now lives at the network peer.)
      uint32_t b =
          TPROTO_GET_PAYLOAD_PARAM32(payloadPtr);  // d3, byte in low 8 bits
      midi_net_send_byte((uint8_t)(b & 0xFFu));
      midiCmdSend++;  // DEBUG
      break;
    }
    case CMD_MIDI_RECV: {
      midiCmdRecv++;  // DEBUG
      // Bconin(3): pop ONE byte (if any) into the shared byte slot, in the low
      // 8 bits of the longword the m68k reads. Bconstat reads the depth (kept
      // current by midi_publish_depth). The m68k spins on the depth before
      // issuing this, so a byte is normally present.
      uint8_t b = 0;
      if (midiInTail != midiInHead) {
        b = midiInQueue[midiInTail];
        midiInTail = (uint16_t)((midiInTail + 1) & (MIDI_IN_QUEUE_SIZE - 1));
      }
      // Write b into all four bytes (raw, no swap) so the m68k reads it whatever
      // byte/endianness it picks up — rules out a read-side byte-order bug.
      WRITE_LONGWORD_RAW((unsigned int)&__rom_in_ram_start__,
                         MIDI_IN_BUFFER_OFFSET, (uint32_t)b * 0x01010101u);
      midi_publish_depth();
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
      midiNetPort = (uint16_t)atoi(e->value);
    }
    e = settings_find_entry(cfg, MIDI_CFG_ENABLED);
    if (e != NULL && e->value[0] != '\0') {
      char c = e->value[0];
      midiEnabled = (c == 't' || c == 'T' || c == '1' || c == 'y' || c == 'Y');
    }
  }
  DPRINTF("MIDI cfg: host=%s port=%u enabled=%d\n", midiNetHost,
          (unsigned)midiNetPort, (int)midiEnabled);
}

// EPIC-06 STORY-04: re-read the endpoint config and restart the connection so a
// host/port change applies live — drop any current connection and reconnect to
// the new endpoint promptly (no backoff wait).
void midi_net_reload(void) {
  midi_load_config();
  midi_net_reset();  // close any live pcb -> MIDI_NET_DOWN, flush the IN queue
  midiNetBackoffMs = MIDI_NET_BACKOFF_MIN_MS;
  midiNetNextAttemptValid = false;  // let midi_net_poll connect on the next tick
}

void midi_init(void) {
  // Load the orchestrator endpoint config (EPIC-06 STORY-01). aconfig_init() ran
  // in main() before emul_start(), so the context is populated.
  midi_load_config();

  // No pending MIDI-IN bytes at boot. The RP owns this field in the served ROM
  // image; the m68k only ever reads it (CMD_MIDI_RECV).
  WRITE_AND_SWAP_LONGWORD((unsigned int)&__rom_in_ram_start__,
                          MIDI_IN_COUNT_OFFSET, 0);
  chandler_addCB(midi_command_cb);
}
