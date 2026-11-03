#ifndef WAV_PLAYER_H
#define WAV_PLAYER_H

#include <Arduino.h>

// HTTP / HTTPS 下載 WAV 到 PSRAM
bool downloadWAV(const char* url);

// 播放已下載的 WAV
bool playWAV();

// 釋放 WAV 緩衝區
void releaseWAV();

#endif
