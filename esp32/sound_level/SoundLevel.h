#pragma once

#include <Arduino.h>
#include <ESP_I2S.h>

struct SoundReading {
    double rmsDbFS = 0.0;
    double dbSPL = 0.0;
    double dBA = 0.0;
    double peak = 0.0;  // Raw peak amplitude of latest processed frame
};

// One I2S bus, two INMP441 microphones: LEFT (L/R=GND), RIGHT (L/R=3.3V).
class SoundLevel {
public:
    SoundLevel(int bclk, int ws, int sd,
               double leftCalibrationOffset, double rightCalibrationOffset);

    bool begin();
    // Reads an interleaved stereo buffer and updates both microphones.
    // Returns true when ~1 second of audio is available for both readings.
    bool update(SoundReading& left, SoundReading& right);

private:
    static constexpr int kSampleRate = 16000;
    static constexpr int kBufferSize = 1024;
    static constexpr double kFullScale = 8388607.0;

    struct HighPass {
        float alpha;
        float previousInput = 0.0f;
        float previousOutput = 0.0f;
        HighPass(float cutoff, float sampleRate);
        float process(float input);
    };

    struct Biquad {
        float b0, b1, b2, a1, a2;
        float z1 = 0.0f, z2 = 0.0f;
        float process(float x);
    };

    struct AWeighting {
        Biquad stages[3] = {
            {0.942252084f, 0.101030443f, 0.002708179f, -0.016647243f, 0.000069283f},
            {1.0f, -2.0f, 1.0f, -1.707050839f, 0.717463706f},
            {1.0f, -2.0f, 1.0f, -1.983886845f, 0.983951753f}
        };
        float process(float input);
    };

    struct Channel {
        explicit Channel(double offset) : calibrationOffset(offset) {}
        HighPass hp{20.0f, (float)kSampleRate};
        AWeighting aFilter;
        double calibrationOffset;
        double squareSum = 0.0;
        double aSquareSum = 0.0;
        double latestFramePeak = 0.0;
        void process(int32_t raw);
        void emit(SoundReading& reading, uint32_t sampleCount);
    };

    static int32_t convertSample(int32_t raw);
    static double rmsToDbFS(double rms);

    int bclk_, ws_, sd_;
    I2SClass i2s_;
    int32_t samples_[kBufferSize] = {};
    Channel left_;
    Channel right_;
    uint32_t sampleCount_ = 0;
};
