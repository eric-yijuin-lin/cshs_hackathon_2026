#include "SoundLevel.h"

// GPIO：BCLK、WS、SD
// Offset：Mic A、Mic B
SoundLevel sound(26, 25, 33, 104.0, 104.0);

void setup()
{
    Serial.begin(115200);

    if (!sound.begin())
    {
        Serial.println("I2S init failed");
        while (true) delay(1000);
    }
}

void loop()
{
    SoundReading micA, micB;

    if (sound.update(micA, micB))
    {
        Serial.printf("Mic A SPL: %.1f\n", micA.dbSPL);
        Serial.printf("Mic B SPL: %.1f\n", micB.dbSPL);

        Serial.printf("Mic A dBA: %.1f\n", micA.dBA);
        Serial.printf("Mic B dBA: %.1f\n", micB.dBA);
    }
}