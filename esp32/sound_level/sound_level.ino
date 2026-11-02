#include "SoundLevel.h"

SoundLevel sound;

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
    SoundReading reading;

    if (sound.update(reading))
    {
        Serial.print("RMS dBFS: ");
        Serial.println(reading.rmsDbFS);

        Serial.print("dB SPL: ");
        Serial.println(reading.dbSPL);

        Serial.print("dBA: ");
        Serial.println(reading.dBA);
    }
}