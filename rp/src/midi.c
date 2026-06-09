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
    default:
      DPRINTF("MIDI: unknown command %04X\n", protocol->command_id);
      break;
  }
}

void midi_init(void) { chandler_addCB(midi_command_cb); }
