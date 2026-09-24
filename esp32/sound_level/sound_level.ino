#include <Arduino.h>
#include <ESP_I2S.h>

#define I2S_BCLK 26
#define I2S_WS   25
#define I2S_SD   33
#define SAMPLE_SIZE 1024
#define SAMPLE_RATE 16000

const double FULL_SCALE = 8388607.0;
const double FULL_SCALE_RMS = FULL_SCALE / sqrt(2.0);


class HighPassFilter
{
private:
    float alpha;
    float previousInput = 0;
    float previousOutput = 0;

public:
    HighPassFilter(float cutoff, float sampleRate)
    {
        float dt = 1.0 / sampleRate;
        float rc = 1.0 / (2.0 * PI * cutoff);
        alpha = rc / (rc + dt);
    }

    float process(float input)
    {
        float output = alpha * (previousOutput + input - previousInput);
        previousInput = input;
        previousOutput = output;

        return output;
    }
    
    void reset()
    {
        previousInput = 0;
        previousOutput = 0;
    }
};


I2SClass I2S;
unsigned long debug_start = 0;
int32_t samples[SAMPLE_SIZE];

double calculateRMS(int32_t samples[], int count);
double rmsToDbFS(double rms);
int32_t convertSample(int32_t raw);

HighPassFilter hp(
    20,
    SAMPLE_RATE
);

void setup()
{
    Serial.begin(115200);

    I2S.setPins(
        I2S_BCLK,   // BCLK
        I2S_WS,     // LRCLK
        -1,         // MCLK 不使用
        I2S_SD      // DIN
        
    );

    bool result = I2S.begin(
        I2S_MODE_STD,
        SAMPLE_RATE,
        I2S_DATA_BIT_WIDTH_32BIT,
        I2S_SLOT_MODE_STEREO,
        I2S_STD_SLOT_LEFT
    );

    if (!result)
    {
        Serial.println("I2S init failed");
        while(1)
        {
            delay(1000);
        }
    }

    Serial.println("I2S ready");
    debug_start = millis();
}

void loop()
{
    size_t bytesRead = I2S.readBytes(
        (char*)samples,
        sizeof(samples)
    );

    int sampleCount = bytesRead / sizeof(int32_t);

    double rms = calculateRMS(
        samples,
        sampleCount
    );

    // 每 500ms 印一次
    if(millis() - debug_start > 500)
    {
        Serial.print("RMS=");
        Serial.println(rms);

        double db = rmsToDbFS(rms);
        Serial.print("dB=");
        Serial.println(db);
        debug_start = millis();
    }
}

double calculateRMS(int32_t samples[], int count)
{
    double sum = 0;
    int validCount = 0;

    for(int i = 0; i < count; i += 2)
    {
        int32_t sample = convertSample(samples[i]);
        float filtered = hp.process(sample);
        sum += filtered * filtered;
        validCount++;
    }

    return sqrt(sum / validCount);
}

double rmsToDbFS(double rms)
{
    if(rms <= 0)
    {
        return -100.0;
    }

    return 20.0 * log10(rms / FULL_SCALE_RMS);
}

int32_t convertSample(int32_t raw)
{
    return raw >> 8;
}

