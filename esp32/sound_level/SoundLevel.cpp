#include "SoundLevel.h"
#include <math.h>

SoundLevel::SoundLevel(int bclk, int ws, int sd,
                       double leftCalibrationOffset, double rightCalibrationOffset)
    : bclk_(bclk), ws_(ws), sd_(sd),
      left_(leftCalibrationOffset), right_(rightCalibrationOffset) {}

SoundLevel::HighPass::HighPass(float cutoff, float sampleRate) {
    const float dt = 1.0f / sampleRate;
    const float rc = 1.0f / (2.0f * PI * cutoff);
    alpha = rc / (rc + dt);
}

float SoundLevel::HighPass::process(float input) {
    const float output = alpha * (previousOutput + input - previousInput);
    previousInput = input;
    previousOutput = output;
    return output;
}

float SoundLevel::Biquad::process(float x) {
    const float y = b0 * x + z1;
    z1 = b1 * x - a1 * y + z2;
    z2 = b2 * x - a2 * y;
    return y;
}

float SoundLevel::AWeighting::process(float x) {
    for (auto& stage : stages) x = stage.process(x);
    return x;
}

int32_t SoundLevel::convertSample(int32_t raw) {
    return raw >> 8;
}

double SoundLevel::rmsToDbFS(double rms) {
    if (rms <= 0.0) return -INFINITY;
    const double fullScaleRms = kFullScale / sqrt(2.0);
    return 20.0 * log10(rms / fullScaleRms);
}

void SoundLevel::Channel::process(int32_t raw) {
    const int32_t sample = SoundLevel::convertSample(raw);
    const double filtered = hp.process((float)sample);
    const double aFiltered = aFilter.process((float)sample);
    squareSum += filtered * filtered;
    aSquareSum += aFiltered * aFiltered;
    const double amplitude = fabs(filtered);
    if (amplitude > latestFramePeak) latestFramePeak = amplitude;
}

void SoundLevel::Channel::emit(SoundReading& reading, uint32_t sampleCount) {
    const double rms = sqrt(squareSum / sampleCount);
    const double aRms = sqrt(aSquareSum / sampleCount);
    reading.rmsDbFS = SoundLevel::rmsToDbFS(rms);
    reading.dbSPL = reading.rmsDbFS + calibrationOffset;
    reading.dBA = SoundLevel::rmsToDbFS(aRms) + calibrationOffset;
    reading.peak = latestFramePeak;
    squareSum = 0.0;
    aSquareSum = 0.0;
}

bool SoundLevel::begin() {
    i2s_.setPins(bclk_, ws_, -1, sd_);
    return i2s_.begin(
        I2S_MODE_STD,
        kSampleRate,
        I2S_DATA_BIT_WIDTH_32BIT,
        I2S_SLOT_MODE_STEREO,
        I2S_STD_SLOT_BOTH
    );
}

bool SoundLevel::update(SoundReading& left, SoundReading& right) {
    const size_t bytesRead = i2s_.readBytes((char*)samples_, sizeof(samples_));
    const int rawCount = bytesRead / sizeof(int32_t);
    const int frameCount = rawCount / 2;
    if (frameCount == 0) return false;

    left_.latestFramePeak = 0.0;
    right_.latestFramePeak = 0.0;
    for (int i = 0; i < frameCount * 2; i += 2) {
        left_.process(samples_[i]);
        right_.process(samples_[i + 1]);
    }
    sampleCount_ += frameCount;
    if (sampleCount_ < kSampleRate) return false;

    left_.emit(left, sampleCount_);
    right_.emit(right, sampleCount_);
    sampleCount_ = 0;
    return true;
}
