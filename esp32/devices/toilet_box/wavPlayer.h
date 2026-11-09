#ifndef WAV_PLAYER_H
#define WAV_PLAYER_H

#include <Arduino.h>

// 取得音檔數量，API 直接回傳整數，失敗回傳 -1
int getWavFileCount(String url);

// 下載指定 index 的 WAV 至 PSRAM；不清除其他已下載音檔
bool downloadWAV(String url, int index);

// 播放已下載的 WAV
bool playWAV(int index);

// 釋放 WAV 緩衝區
void releaseWAV();

#endif
