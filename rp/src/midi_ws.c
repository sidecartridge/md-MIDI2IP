/**
 * File: midi_ws.c
 * Author: Diego Parrilla Santamaría
 * Date: June 2026
 * Copyright: 2026 - GOODDATA LABS SL
 * Description: RFC 6455 client-side WebSocket helpers (EPIC-13 STORY-05). Pure C,
 * no lwIP / pico dependency. See midi_ws.h.
 */
#include "midi_ws.h"

#include <string.h>

// --- base64 --------------------------------------------------------------
static const char B64[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

void midi_ws_base64(const uint8_t *in, size_t n, char *out) {
  size_t i = 0, o = 0;
  while (i + 3 <= n) {
    uint32_t v = ((uint32_t)in[i] << 16) | ((uint32_t)in[i + 1] << 8) | in[i + 2];
    out[o++] = B64[(v >> 18) & 0x3F];
    out[o++] = B64[(v >> 12) & 0x3F];
    out[o++] = B64[(v >> 6) & 0x3F];
    out[o++] = B64[v & 0x3F];
    i += 3;
  }
  size_t rem = n - i;
  if (rem == 1) {
    uint32_t v = (uint32_t)in[i] << 16;
    out[o++] = B64[(v >> 18) & 0x3F];
    out[o++] = B64[(v >> 12) & 0x3F];
    out[o++] = '=';
    out[o++] = '=';
  } else if (rem == 2) {
    uint32_t v = ((uint32_t)in[i] << 16) | ((uint32_t)in[i + 1] << 8);
    out[o++] = B64[(v >> 18) & 0x3F];
    out[o++] = B64[(v >> 12) & 0x3F];
    out[o++] = B64[(v >> 6) & 0x3F];
    out[o++] = '=';
  }
  out[o] = '\0';
}

// --- SHA-1 (RFC 3174) ----------------------------------------------------
static inline uint32_t rol(uint32_t v, int b) { return (v << b) | (v >> (32 - b)); }

static void sha1_block(uint32_t state[5], const uint8_t blk[64]) {
  uint32_t w[80];
  for (int i = 0; i < 16; i++) {
    w[i] = ((uint32_t)blk[i * 4] << 24) | ((uint32_t)blk[i * 4 + 1] << 16) |
           ((uint32_t)blk[i * 4 + 2] << 8) | blk[i * 4 + 3];
  }
  for (int i = 16; i < 80; i++) {
    w[i] = rol(w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16], 1);
  }
  uint32_t a = state[0], b = state[1], c = state[2], d = state[3], e = state[4];
  for (int i = 0; i < 80; i++) {
    uint32_t f, k;
    if (i < 20) {
      f = (b & c) | ((~b) & d);
      k = 0x5A827999;
    } else if (i < 40) {
      f = b ^ c ^ d;
      k = 0x6ED9EBA1;
    } else if (i < 60) {
      f = (b & c) | (b & d) | (c & d);
      k = 0x8F1BBCDC;
    } else {
      f = b ^ c ^ d;
      k = 0xCA62C1D6;
    }
    uint32_t t = rol(a, 5) + f + e + k + w[i];
    e = d;
    d = c;
    c = rol(b, 30);
    b = a;
    a = t;
  }
  state[0] += a;
  state[1] += b;
  state[2] += c;
  state[3] += d;
  state[4] += e;
}

static void sha1(const uint8_t *data, size_t len, uint8_t out[20]) {
  uint32_t state[5] = {0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476,
                       0xC3D2E1F0};
  uint8_t blk[64];
  size_t i = 0;
  while (len - i >= 64) {
    sha1_block(state, data + i);
    i += 64;
  }
  size_t rem = len - i;
  memset(blk, 0, sizeof(blk));
  memcpy(blk, data + i, rem);
  blk[rem] = 0x80;
  if (rem >= 56) {
    sha1_block(state, blk);
    memset(blk, 0, sizeof(blk));
  }
  uint64_t ml = (uint64_t)len * 8;
  for (int j = 0; j < 8; j++) {
    blk[56 + j] = (uint8_t)(ml >> (56 - j * 8));
  }
  sha1_block(state, blk);
  for (int j = 0; j < 5; j++) {
    out[j * 4] = (uint8_t)(state[j] >> 24);
    out[j * 4 + 1] = (uint8_t)(state[j] >> 16);
    out[j * 4 + 2] = (uint8_t)(state[j] >> 8);
    out[j * 4 + 3] = (uint8_t)(state[j]);
  }
}

#define WS_GUID "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

void midi_ws_accept_key(const char *client_key, char *out) {
  uint8_t buf[96];  // client key (<= 24) + GUID (36); bounded
  size_t kl = strlen(client_key);
  size_t gl = sizeof(WS_GUID) - 1;
  if (kl + gl > sizeof(buf)) {
    out[0] = '\0';
    return;
  }
  memcpy(buf, client_key, kl);
  memcpy(buf + kl, WS_GUID, gl);
  uint8_t dig[20];
  sha1(buf, kl + gl, dig);
  midi_ws_base64(dig, 20, out);
}

// --- framing -------------------------------------------------------------
size_t midi_ws_build_frame(uint8_t *out, uint8_t opcode, const uint8_t *payload,
                           size_t len, const uint8_t mask_key[4]) {
  size_t o = 0;
  out[o++] = (uint8_t)(0x80u | (opcode & 0x0Fu));  // FIN + opcode
  if (len < 126) {
    out[o++] = (uint8_t)(0x80u | (uint8_t)len);  // mask bit + length
  } else {
    out[o++] = (uint8_t)(0x80u | 126u);
    out[o++] = (uint8_t)(len >> 8);
    out[o++] = (uint8_t)(len & 0xFF);
  }
  out[o++] = mask_key[0];
  out[o++] = mask_key[1];
  out[o++] = mask_key[2];
  out[o++] = mask_key[3];
  for (size_t i = 0; i < len; i++) {
    out[o++] = (uint8_t)(payload[i] ^ mask_key[i & 3]);
  }
  return o;
}

// --- decoder -------------------------------------------------------------
enum { S_OP = 0, S_LEN, S_EXT, S_PAYLOAD };

void midi_ws_decoder_init(midi_ws_decoder *d) {
  memset(d, 0, sizeof(*d));
  d->state = S_OP;
}

bool midi_ws_decode(midi_ws_decoder *d, const uint8_t *data, size_t n,
                    void (*on_data)(const uint8_t *p, size_t len, void *ctx),
                    void (*on_ctl)(uint8_t opcode, const uint8_t *p, size_t len,
                                   void *ctx),
                    void *ctx) {
  size_t i = 0;
  while (i < n) {
    switch (d->state) {
      case S_OP: {
        uint8_t b = data[i++];
        d->opcode = (uint8_t)(b & 0x0F);
        d->is_control = (d->opcode & 0x08) != 0;
        d->ctl_len = 0;
        d->state = S_LEN;
        break;
      }
      case S_LEN: {
        uint8_t b = data[i++];
        if (b & 0x80) {
          return false;  // server-to-client frames must not be masked
        }
        uint8_t l = (uint8_t)(b & 0x7F);
        if (d->is_control && l > 125) {
          return false;  // control frames carry <= 125 bytes
        }
        if (l < 126) {
          d->remaining = l;
          d->state = S_PAYLOAD;
        } else if (l == 126) {
          d->remaining = 0;
          d->ext_left = 2;
          d->state = S_EXT;
        } else {
          d->remaining = 0;
          d->ext_left = 8;
          d->state = S_EXT;
        }
        break;
      }
      case S_EXT: {
        d->remaining = (d->remaining << 8) | data[i++];
        if (--d->ext_left == 0) {
          d->state = S_PAYLOAD;
        }
        break;
      }
      case S_PAYLOAD: {
        if (d->remaining > 0) {
          size_t avail = n - i;
          size_t take = (d->remaining < (uint64_t)avail) ? (size_t)d->remaining
                                                         : avail;
          if (d->is_control) {
            for (size_t k = 0; k < take; k++) {
              if (d->ctl_len < sizeof(d->ctl)) {
                d->ctl[d->ctl_len++] = data[i + k];
              }
            }
          } else if (on_data) {
            on_data(data + i, take, ctx);
          }
          i += take;
          d->remaining -= take;
        }
        if (d->remaining == 0) {  // frame complete (also the empty-frame case)
          if (d->is_control && on_ctl) {
            on_ctl(d->opcode, d->ctl, d->ctl_len, ctx);
          }
          d->state = S_OP;
        }
        break;
      }
      default:
        return false;
    }
  }
  // A zero-length frame whose header ended exactly at the buffer boundary is
  // complete now (the loop exited before re-entering S_PAYLOAD).
  if (d->state == S_PAYLOAD && d->remaining == 0) {
    if (d->is_control && on_ctl) {
      on_ctl(d->opcode, d->ctl, d->ctl_len, ctx);
    }
    d->state = S_OP;
  }
  return true;
}
