#include "SoundLevel.h"
#include <math.h>

SoundLevel::SoundLevel(int bclk, int ws, int sd)
    : bclk_(bclk), ws_(ws), sd_(sd) {}

SoundLevel::HighPass::HighPass(float cutoff, float sampleRate) {
    float dt = 1.0f / sampleRate;
    float rc = 1.0f / (2.0f * PI * cutoff);
    alpha = rc / (rc + dt);
}

float SoundLevel::HighPass::process(float input) {
    float output = alpha * (previousOutput + input - previousInput);
    previousInput = input;
    previousOutput = output;
    return output;
}

float SoundLevel::Biquad::process(float x) {
    float y = b0 * x + z1;
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

bool SoundLevel::begin() {
    i2s_.setPins(bclk_, ws_, -1, sd_);
    return i2s_.begin(
        I2S_MODE_STD,
        kSampleRate,
        I2S_DATA_BIT_WIDTH_32BIT,
        I2S_SLOT_MODE_STEREO,
        I2S_STD_SLOT_LEFT
    );
}

bool SoundLevel::update(SoundReading& reading) {
    size_t bytesRead = i2s_.readBytes((char*)samples_, sizeof(samples_));
    const int rawCount = bytesRead / sizeof(int32_t);
    // Stereo interleaved: only complete L/R pairs, using left slots.
    const int validCount = rawCount / 2;
    if (validCount == 0) return false;

    double frameSquareSum = 0;
    double frameASquareSum = 0;
    double peak = 0;
    for (int i = 0; i < validCount * 2; i += 2) {
        int32_t sample = convertSample(samples_[i]);
        double filtered = hp_.process((float)sample);
        double aFiltered = aFilter_.process((float)sample);
        frameSquareSum += filtered * filtered;
        frameASquareSum += aFiltered * aFiltered;
        double amplitude = fabs(filtered);
        if (amplitude > peak) peak = amplitude;
    }

    squareSum_ += frameSquareSum;
    aSquareSum_ += frameASquareSum;
    sampleCount_ += validCount;

    if (sampleCount_ < kSampleRate) return false;

    double rms = sqrt(squareSum_ / sampleCount_);
    double aRms = sqrt(aSquareSum_ / sampleCount_);
    reading.rmsDbFS = rmsToDbFS(rms);
    reading.dbSPL = reading.rmsDbFS + kCalibrationOffset;
    reading.dBA = rmsToDbFS(aRms) + kCalibrationOffset;
    reading.peak = peak; // Most recent frame; not a 1-second peak hold.

    squareSum_ = 0;
    aSquareSum_ = 0;
    sampleCount_ = 0;
    return true;
}
