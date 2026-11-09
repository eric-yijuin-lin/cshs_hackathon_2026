#include "WavPlayer.h"
#include <WiFi.h>
#include <WiFiClient.h>
#include <map>
#include <climits>
#include <HTTPClient.h>
#include <ESP_I2S.h>
#include <esp_heap_caps.h>

// I2S 腳位
#define I2S_BCLK 41
#define I2S_LRC  42
#define I2S_DOUT 21

// 下載設定
static constexpr uint32_t DOWNLOAD_IDLE_TIMEOUT = 10000;
static constexpr size_t DOWNLOAD_CHUNK_SIZE = 2048;

// 私有變數
static I2SClass I2S;
struct WavData {
  uint8_t* buffer;
  size_t size;
};

// index -> WAV 資料；每個音檔獨立存放於 PSRAM
static std::map<int, WavData> wavFiles;

// 共用 HTTP GET 初始化與狀態檢查（僅支援內網 HTTP）
static bool startHttpGet(HTTPClient& http, WiFiClient& client, const String& url) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected!");
    return false;
  }

  if (!url.startsWith("http://")) {
    Serial.println("Only HTTP URLs are supported!");
    return false;
  }

  http.setTimeout(DOWNLOAD_IDLE_TIMEOUT);
  client.setTimeout(DOWNLOAD_IDLE_TIMEOUT);

  Serial.printf("HTTP GET: %s\n", url.c_str());
  if (!http.begin(client, url)) {
    Serial.println("HTTP begin failed!");
    return false;
  }

  int code = http.GET();
  if (code != HTTP_CODE_OK) {
    Serial.printf("HTTP error: %d\n", code);
    http.end();
    return false;
  }

  return true;
}

// Little-endian 讀取
static uint16_t read16(const uint8_t* p) {
  return (uint16_t)p[0] |
         ((uint16_t)p[1] << 8);
}

static uint32_t read32(const uint8_t* p) {
  return (uint32_t)p[0] |
         ((uint32_t)p[1] << 8) |
         ((uint32_t)p[2] << 16) |
         ((uint32_t)p[3] << 24);
}

// 釋放所有已下載的 WAV
void releaseWAV() {
  for (auto& item : wavFiles) {
    free(item.second.buffer);
  }
  wavFiles.clear();
}

// 取得音檔數量，API 直接回傳整數
// 失敗回傳 -1
int getWavFileCount(String url) {
  WiFiClient client;
  HTTPClient http;

  if (!startHttpGet(http, client, url)) return -1;

  String response = http.getString();
  http.end();
  response.trim();

  // 確認回傳內容為非負整數
  if (response.isEmpty()) return -1;

  for (size_t i = 0; i < response.length(); i++) {
    if (!isDigit(response[i])) {
      Serial.println("Invalid WAV count!");
      return -1;
    }
  }

  long count = response.toInt();
  if (count < 0 || count > INT_MAX) return -1;

  Serial.printf("WAV file count: %ld\n", count);
  return (int)count;
}

// 下載指定 index 的 WAV 至 PSRAM；不清除其他已下載音檔
bool downloadWAV(String url, int index) {
  if (index < 0) {
    Serial.println("Invalid WAV index!");
    return false;
  }

  if (!psramFound()) {
    Serial.println("PSRAM not found!");
    return false;
  }

  // 原始 URL 已有 query 時使用 &，否則使用 ?
  url += (url.indexOf('?') >= 0 ? "&index=" : "?index=");
  url += String(index);

  WiFiClient client;
  HTTPClient http;
  if (!startHttpGet(http, client, url)) return false;

  int length = http.getSize();
  if (length <= 44) {
    Serial.println("Invalid WAV length (Content-Length required)!");
    http.end();
    return false;
  }

  Serial.printf("Downloading %s\n", url.c_str());
  Serial.printf("total %d bytes...\n", length);

  uint8_t* buffer = (uint8_t*)heap_caps_malloc(
    (size_t)length, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT
  );
  if (buffer == nullptr) {
    Serial.println("PSRAM allocation failed!");
    http.end();
    return false;
  }

  WiFiClient* stream = http.getStreamPtr();
  size_t received = 0;
  unsigned long lastDataTime = millis();

  while (received < (size_t)length) {
    int availableBytes = stream->available();

    if (availableBytes > 0) {
      size_t remaining = (size_t)length - received;
      size_t chunk = min(
        (size_t)availableBytes,
        min(DOWNLOAD_CHUNK_SIZE, remaining)
      );

      size_t n = stream->readBytes(buffer + received, chunk);
      if (n > 0) {
        received += n;
        lastDataTime = millis();
      }
    }

    if (!stream->connected() && stream->available() == 0) {
      Serial.println("Connection closed!");
      break;
    }

    if (millis() - lastDataTime > DOWNLOAD_IDLE_TIMEOUT) {
      Serial.println("Download timeout!");
      break;
    }
    delay(1);
  }

  http.end();
  Serial.printf("Received: %u / %d bytes\n", (unsigned)received, length);

  if (received != (size_t)length) {
    Serial.println("Incomplete download!");
    free(buffer);
    return false;
  }

  if (memcmp(buffer, "RIFF", 4) != 0 ||
      memcmp(buffer + 8, "WAVE", 4) != 0) {
    Serial.println("Invalid WAV file!");
    free(buffer);
    return false;
  }

  // 同一 index 重新下載時，只取代該筆；其他 index 保留
  auto existing = wavFiles.find(index);
  if (existing != wavFiles.end()) {
    free(existing->second.buffer);
    existing->second = {buffer, received};
  } else {
    wavFiles.emplace(index, WavData{buffer, received});
  }

  Serial.printf("WAV [%d] downloaded to PSRAM!\n", index);
  return true;
}

// 將完整資料寫入 I2S
static bool writeI2S(const uint8_t* data, size_t size) {
  size_t sent = 0;

  while (sent < size) {
    size_t n = I2S.write(data + sent, size - sent);

    if (n == 0) {
      Serial.println("I2S write failed!");
      return false;
    }

    sent += n;
  }

  return true;
}

// 播放 WAV
// 根據 index 播放已下載的 WAV
bool playWAV(int index) {
  auto it = wavFiles.find(index);
  if (it == wavFiles.end() || it->second.buffer == nullptr || it->second.size < 44) {
    Serial.printf("WAV [%d] not loaded!\n", index);
    return false;
  }

  const uint8_t* wavBuffer = it->second.buffer;
  const size_t wavSize = it->second.size;

  uint16_t audioFormat = 0;
  uint16_t channels = 0;
  uint16_t bitsPerSample = 0;
  uint32_t sampleRate = 0;

  size_t dataOffset = 0;
  size_t dataSize = 0;

  bool foundFmt = false;
  bool foundData = false;

  size_t offset = 12;

  // 解析 RIFF chunks
  while (offset + 8 <= wavSize) {
    const uint8_t* chunk = wavBuffer + offset;

    uint32_t chunkSize = read32(chunk + 4);
    size_t start = offset + 8;

    if (chunkSize > wavSize - start) {
      Serial.println("Invalid WAV chunk!");
      return false;
    }

    if (memcmp(chunk, "fmt ", 4) == 0) {
      if (chunkSize < 16) return false;

      audioFormat = read16(wavBuffer + start);
      channels = read16(wavBuffer + start + 2);
      sampleRate = read32(wavBuffer + start + 4);
      bitsPerSample = read16(wavBuffer + start + 14);

      foundFmt = true;
    }

    if (memcmp(chunk, "data", 4) == 0) {
      dataOffset = start;
      dataSize = chunkSize;
      foundData = true;
    }

    size_t paddedSize = (size_t)chunkSize + (chunkSize & 1);
    if (paddedSize > wavSize - start) break;

    offset = start + paddedSize;
  }

  if (!foundFmt || !foundData) {
    Serial.println("Missing WAV chunks!");
    return false;
  }

  Serial.printf("Sample rate: %u Hz\n", sampleRate);
  Serial.printf("Channels: %u\n", channels);
  Serial.printf("Bits: %u\n", bitsPerSample);

  if (audioFormat != 1 ||
      bitsPerSample != 16 ||
      (channels != 1 && channels != 2) ||
      sampleRate == 0 ||
      dataSize == 0 ||
      dataSize % (channels * 2) != 0) {
    Serial.println("Unsupported WAV format!");
    return false;
  }

  I2S.setPins(I2S_BCLK, I2S_LRC, I2S_DOUT);

  if (!I2S.begin(
        I2S_MODE_STD,
        sampleRate,
        I2S_DATA_BIT_WIDTH_16BIT,
        I2S_SLOT_MODE_STEREO
      )) {
    Serial.println("I2S initialization failed!");
    return false;
  }

  Serial.println("Playing WAV...");

  const uint8_t* pcm = wavBuffer + dataOffset;
  bool success = true;

  if (channels == 2) {
    // Stereo：直接輸出
    size_t pos = 0;

    while (pos < dataSize) {
      size_t count = min((size_t)1024, dataSize - pos);

      if (!writeI2S(pcm + pos, count)) {
        success = false;
        break;
      }

      pos += count;
    }

  } else {
    // Mono：轉成左右相同的 Stereo
    int16_t stereo[256 * 2];

    size_t samples = dataSize / 2;
    size_t pos = 0;

    while (pos < samples) {
      size_t count = min((size_t)256, samples - pos);

      for (size_t i = 0; i < count; i++) {
        int16_t sample = (int16_t)read16(
          pcm + (pos + i) * 2
        );

        stereo[i * 2] = sample;
        stereo[i * 2 + 1] = sample;
      }

      if (!writeI2S(
            (const uint8_t*)stereo,
            count * 4
          )) {
        success = false;
        break;
      }

      pos += count;
    }
  }

  // 送出靜音，避免最後一段音訊被截斷
  int16_t silence[512] = {0};

  for (int i = 0; i < 8; i++) {
    if (!writeI2S(
          (const uint8_t*)silence,
          sizeof(silence)
        )) {
      success = false;
      break;
    }
  }

  I2S.end();

  if (success) {
    Serial.println("Playback finished!");
  }

  return success;
}
