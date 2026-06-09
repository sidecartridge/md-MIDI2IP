/**
 * File: midi.c
 * Author: Diego Parrilla Santamaría
 * Date: June 2026
 * Copyright: 2026 - GOODDATA LABS SL
 * Description: MIDI-to-IP command handler (RP side).
 *
 * EPIC-01 STORY-01: services CMD_MIDI_SAVE_VECTOR. The m68k installs its
 * BIOS/XBIOS trap hooks using the XBRA convention, but the XBRA <old>
 * field lives in the cartridge ROM, which the m68k can't write. So it
 * hands us the original vector and the field's address; we patch the
 * field in the served ROM image so the m68k handler can chain through it.
 * This mirrors how md-drives-emulator saves the GEMDRIVE/FLOPPY vectors.
 */

#include "midi.h"

#include "chandler.h"
#include "constants.h"  // __rom_in_ram_start__
#include "debug.h"
#include "lwip/ip_addr.h"
#include "lwip/tcp.h"
#include "memfunc.h"    // WRITE_AND_SWAP_LONGWORD
#include "network.h"    // network_getCurrentIp
#include "pico/time.h"
#include "tprotocol.h"  // TransmissionProtocol, TPROTO_* payload macros

// --- EPIC-02 IN queue ---
// Bytes the RP owes the m68k. In the loopback, CMD_MIDI_SEND echoes the OUT byte
// straight in here; CMD_MIDI_RECV drains it into the shared MIDI_IN_BUFFER.
// (EPIC-03 fills this from the network instead.) Single producer / single
// consumer, both on the bus loop, so no locking. Size is a power of two.
#define MIDI_IN_QUEUE_SIZE 1024
static uint8_t midiInQueue[MIDI_IN_QUEUE_SIZE];
static uint16_t midiInHead = 0;  // next write
static uint16_t midiInTail = 0;  // next read

static inline void __not_in_flash_func(midi_in_push)(uint8_t b) {
  uint16_t next = (uint16_t)((midiInHead + 1) & (MIDI_IN_QUEUE_SIZE - 1));
  if (next == midiInTail) return;  // full: drop
  midiInQueue[midiInHead] = b;
  midiInHead = next;
}

// --- EPIC-03 STORY-01: TCP client to the orchestrator ---
// Connection lifecycle only: connect to a hardcoded dev endpoint and track
// state. Sending (STORY-02) and receive→IN-queue (STORY-03) come next; for now
// the receive callback discards data. EPIC-04 makes the endpoint configurable.
//
// DEV: set MIDI_NET_HOST to the machine running the echo peer (see the EPIC-03
// STORY-05 echo server). The RP is a raw-TCP client (lwIP NO_SYS poll mode), so
// everything below runs from the main loop / lwIP poll context — no locking.
#define MIDI_NET_HOST "192.168.1.41"  // DEV: laptop running tools/echo_peer.py
#define MIDI_NET_PORT 5005
#define MIDI_NET_RETRY_MS 3000

typedef enum {
  MIDI_NET_DOWN = 0,
  MIDI_NET_CONNECTING,
  MIDI_NET_UP,
} midi_net_state_t;

static midi_net_state_t midiNetState = MIDI_NET_DOWN;
static struct tcp_pcb *midiNetPcb = NULL;
static absolute_time_t midiNetNextAttempt;
static bool midiNetNextAttemptValid = false;

// Drop the PCB and go DOWN. Safe to call from any of our callbacks.
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
  tcp_recved(pcb, p->tot_len);
  pbuf_free(p);
  return ERR_OK;
}

static void midi_net_err_cb(void *arg, err_t err) {
  (void)arg;
  // lwIP has already freed the PCB on error.
  midiNetPcb = NULL;
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
  DPRINTF("MIDI net: connected to %s:%d\n", MIDI_NET_HOST, MIDI_NET_PORT);
  return ERR_OK;
}

static void midi_net_try_connect(void) {
  ip_addr_t ip;
  if (!ipaddr_aton(MIDI_NET_HOST, &ip)) {
    return;
  }
  midiNetPcb = tcp_new();
  if (midiNetPcb == NULL) {
    return;
  }
  tcp_nagle_disable(midiNetPcb);  // TCP_NODELAY — MIDI is latency-sensitive (D-03/C-01)
  tcp_arg(midiNetPcb, NULL);
  tcp_recv(midiNetPcb, midi_net_recv_cb);
  tcp_err(midiNetPcb, midi_net_err_cb);
  midiNetState = MIDI_NET_CONNECTING;
  if (tcp_connect(midiNetPcb, &ip, MIDI_NET_PORT, midi_net_connected_cb) !=
      ERR_OK) {
    midi_net_reset();
  }
}

// STORY-02: send one OUT byte to the orchestrator. Dropped if the link is down
// (gameplay needs the peer up; STORY-04 surfaces link state). tcp_output flushes
// immediately — TCP_NODELAY, MIDI is latency-sensitive (C-01).
static void midi_net_send_byte(uint8_t b) {
  if (midiNetState != MIDI_NET_UP || midiNetPcb == NULL) {
    return;
  }
  if (tcp_write(midiNetPcb, &b, 1, TCP_WRITE_FLAG_COPY) == ERR_OK) {
    tcp_output(midiNetPcb);
  }
}

// Drive the connection. Call once per main-loop iteration (poll context). When
// down, retries every MIDI_NET_RETRY_MS once Wi-Fi has an IP.
void midi_net_poll(void) {
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
    return;  // waiting for the retry interval
  }
  midiNetNextAttemptValid = true;
  midiNetNextAttempt = make_timeout_time_ms(MIDI_NET_RETRY_MS);
  midi_net_try_connect();
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
      // m68k shipped an OUT byte — send it to the orchestrator. (Was the EPIC-02
      // local echo; the echo now lives at the network peer.)
      uint32_t b = TPROTO_GET_PAYLOAD_PARAM32(payloadPtr);  // d3, byte in low 8 bits
      midi_net_send_byte((uint8_t)(b & 0xFFu));
      break;
    }
    case CMD_MIDI_RECV: {
      // Drain up to MIDI_IN_BUFFER_SIZE pending bytes into the shared buffer
      // (byte-swapped per 16-bit word so the m68k reads them in order), then
      // write the count. Same shape as GEMDRIVE's READ_BUFFER / READ_BYTES.
      uint8_t *buf = (uint8_t *)((unsigned int)&__rom_in_ram_start__ +
                                 MIDI_IN_BUFFER_OFFSET);
      uint16_t n = 0;
      while (n < MIDI_IN_BUFFER_SIZE && midiInTail != midiInHead) {
        buf[n++] = midiInQueue[midiInTail];
        midiInTail = (uint16_t)((midiInTail + 1) & (MIDI_IN_QUEUE_SIZE - 1));
      }
      if (n & 1) buf[n] = 0;  // pad for the 16-bit swap
      CHANGE_ENDIANESS_BLOCK16(buf, n + (n & 1));
      WRITE_AND_SWAP_LONGWORD((unsigned int)&__rom_in_ram_start__,
                              MIDI_IN_COUNT_OFFSET, n);
      break;
    }
    default:
      DPRINTF("MIDI: unknown command %04X\n", protocol->command_id);
      break;
  }
}

void midi_init(void) {
  // No pending MIDI-IN bytes at boot. The RP owns this field in the served ROM
  // image; the m68k only ever reads it (CMD_MIDI_RECV).
  WRITE_AND_SWAP_LONGWORD((unsigned int)&__rom_in_ram_start__,
                          MIDI_IN_COUNT_OFFSET, 0);
  chandler_addCB(midi_command_cb);
}
