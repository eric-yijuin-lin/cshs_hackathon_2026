#pragma once

#include <Arduino.h>
#include <ESP_I2S.h>

struct SoundReading {
    double rmsDbFS;
    double dbSPL;
    double dBA;
    double peak;  // Raw, filtered peak amplitude for the latest frame
};

class SoundLevel {
public:
    SoundLevel(int bclk = 26, int ws = 25, int sd = 33);

    bool begin();
    // Read/process one audio buffer. Returns true when ~1 s of samples is ready.
    bool update(SoundReading& reading);

private:
    static constexpr int kSampleRate = 16000;
    static constexpr int kBufferSize = 1024;
    static constexpr double kFullScale = 8388607.0;
    static constexpr double kCalibrationOffset = 104.0;

    struct HighPass {
        float alpha;
        float previousInput = 0;
        float previousOutput = 0;
        HighPass(float cutoff, float sampleRate);
        float process(float input);
    };

    struct Biquad {
        float b0, b1, b2, a1, a2;
        float z1 = 0, z2 = 0;
        float process(float x);
    };

    struct AWeighting {
        Biquad stages[3] = {
            {0.942252084f, 0.101030443f, 0.002708179f, -0.016647243f, 0.000069283f},
            {1.0f, -2.0f, 1.0f, -1.707050839f, 0.717463706f},
            {1.0f, -2.0f, 1.0f, -1.983886845f, 0.983951753f}
        };
        float process(float x);
    };

    static double rmsToDbFS(double rms);
    static int32_t convertSample(int32_t raw);

    int bclk_, ws_, sd_;
    I2SClass i2s_;
    int32_t samples_[kBufferSize] = {};
    HighPass hp_{20.0f, (float)kSampleRate};
    AWeighting aFilter_;
    double squareSum_ = 0;
    double aSquareSum_ = 0;
    uint32_t sampleCount_ = 0;
};
