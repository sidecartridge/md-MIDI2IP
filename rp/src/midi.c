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
#include "memfunc.h"    // WRITE_AND_SWAP_LONGWORD
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
      // m68k shipped an OUT byte. Loopback: echo it straight into the IN queue.
      uint32_t b = TPROTO_GET_PAYLOAD_PARAM32(payloadPtr);  // d3, byte in low 8 bits
      midi_in_push((uint8_t)(b & 0xFFu));
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
