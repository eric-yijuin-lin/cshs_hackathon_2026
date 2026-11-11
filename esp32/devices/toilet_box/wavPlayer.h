#ifndef WAV_PLAYER_H
#define WAV_PLAYER_H

#include <Arduino.h>

bool loadWavFromSD();

// 播放已下載的 WAV
bool playWAV(String filename);

// 釋放 WAV 緩衝區
void releaseWAV();

#endif
