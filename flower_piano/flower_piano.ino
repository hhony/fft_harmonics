#include "Adafruit_WS2801.h"
#include "SPI.h" // Comment out this line if using Trinket or Gemma
#ifdef __AVR_ATtiny85__
 #include <avr/power.h>
#endif

int _pixels = 10;

//Variables for LEDs
uint8_t dataPin[4]  = {2, 4, 6, 8}; // Yellow wire on Adafruit Pixels
uint8_t clockPin[4] = {3, 5, 7, 9}; // Green wire on Adafruit Pixels

// microphone
const uint8_t microphonePin = 0;    // the microphone positive terminal will connect to analog pin A0 to be read
int _mic_reading;                   // the variable that will hold the value read from the microphone each time
const int _mic_threshold = 100;    // the microphone threshold sound level at which the LED will turn on
int _timer = 0;


// Set the first variable to the NUMBER of pixels. 25 = 25 pixels in a row
Adafruit_WS2801 strip0 = Adafruit_WS2801(_pixels, dataPin[0], clockPin[0]);
Adafruit_WS2801 strip1 = Adafruit_WS2801(_pixels, dataPin[1], clockPin[1]);
Adafruit_WS2801 strip2 = Adafruit_WS2801(_pixels, dataPin[2], clockPin[2]);
Adafruit_WS2801 strip3 = Adafruit_WS2801(_pixels, dataPin[3], clockPin[3]);

void setup() {
#if defined(__AVR_ATtiny85__) && (F_CPU == 16000000L)
  clock_prescale_set(clock_div_1); // Enable 16 MHz on Trinket
#endif
  Serial.begin(9600);
  strip0.begin();
  strip0.show();
  // strip1.begin();
  // strip1.show();
  // strip2.begin();
  // strip2.show();
  // strip3.begin();
  // strip3.show();
  pinMode(13, OUTPUT);
}

uint8_t STD_FADE = 0;
uint8_t MAJ_FADE = 0;
uint8_t MIN_FADE = 0;

#define trigger 1000
char _byte = 0;

uint8_t _delay = 0;


uint32_t Color(uint8_t r, uint8_t g, uint8_t b) {
  uint32_t c = 0;
  c = r;
  c <<= 8;
  c |= g;
  c <<= 8;
  c |= b;
  return c;
}


uint32_t Wheel(byte WheelPos) { // all colors full bright
  if (WheelPos < 85) {
    return Color((WheelPos * 3), (255 - WheelPos * 3), 0 );
  } else if (WheelPos < 170) {
    WheelPos -= 85;
    return Color(255 - WheelPos * 3, 0, WheelPos * 3);
  } else {
    WheelPos -= 170;
    return Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
}

void rainbowCycle(uint8_t strip, uint8_t wait, uint8_t cycles=5) {
  for (int j = 0; j < 256 * cycles; j++) { // 5 cycles of all 256 colors in the wheel
    // tricky math! we use each pixel as a fraction of the full 96-color wheel
    // (thats the i / strip.numPixels() part)
    // Then add in j which makes the colors go around per pixel
    // the % 96 is to make the wheel cycle around
    switch (strip) {
      case 0:
        for (int i = 0; i < strip0.numPixels(); i++) {
          strip0.setPixelColor(i, Wheel(((i * 256 / strip0.numPixels()) + j) % 256));
        }
        strip0.show();
        break;
      case 1:
        for (int i = 0; i < strip1.numPixels(); i++) {
          strip1.setPixelColor(i, Wheel(((i * 256 / strip1.numPixels()) + j) % 256));
        }
        strip1.show();
        break;
      case 2:
        for (int i = 0; i < strip2.numPixels(); i++) {
          strip2.setPixelColor(i, Wheel(((i * 256 / strip2.numPixels()) + j) % 256));
        }
        strip2.show();
        break;
      case 3:
        for (int i = 0; i < strip3.numPixels(); i++) {
          strip3.setPixelColor(i, Wheel(((i * 256 / strip3.numPixels()) + j) % 256));
        }
        strip3.show();
        break;
    }
    if (Serial.peek() > 0) {
      break;
    }
    delay(wait);
  }
}


uint32_t get_color_chord(uint8_t r, uint8_t g, uint8_t b, uint8_t delta) {
  _delay = delta;
  return Color(r, g, b);
}


uint32_t get_color(char _byte) {
  if ( _byte > 0 ) {
    switch( (int)_byte ) {
      //
      // standard
      //
      case 0x21:
        return get_color_chord(102, 172,  86, STD_FADE);
      case 0x22:
        return get_color_chord( 92, 154,  77, STD_FADE);
      case 0x23:
        return get_color_chord( 81, 138,  44, STD_FADE);
      case 0x24:
        return get_color_chord( 70, 125,  41, STD_FADE);
      case 0x25:
        return get_color_chord( 61, 114,  34, STD_FADE);
      case 0x26:
        return get_color_chord( 71, 130,  74, STD_FADE);
      case 0x27:
        return get_color_chord(116, 194,  95, STD_FADE);
      case 0x28:
        return get_color_chord(107, 171,  59, STD_FADE);
      case 0x29:
        return get_color_chord( 91, 151,  51, STD_FADE);
      case 0x2A:
        return get_color_chord( 71, 130,  74, STD_FADE);
      case 0x2B:
        return get_color_chord(  0, 169, 158, STD_FADE);
      case 0x2C:
        return get_color_chord(  0, 144, 163, STD_FADE);
      //
      // cooler
      //
      case 0x31:
        return get_color_chord(  1, 146, 201, MAJ_FADE);
      case 0x32:
        return get_color_chord(  0, 128, 185, MAJ_FADE);
      case 0x33:
        return get_color_chord(  0, 110, 171, MAJ_FADE);
      case 0x34:
        return get_color_chord(  0,  98, 157, MAJ_FADE);
      case 0x35:
        return get_color_chord(  0, 110, 159, MAJ_FADE);
      case 0x36:
        return get_color_chord(  0, 109, 148, MAJ_FADE);
      case 0x37:
        return get_color_chord(  0, 110, 159, MAJ_FADE);
      case 0x38:
        return get_color_chord( 14, 141, 192, MAJ_FADE);
      case 0x39:
        return get_color_chord( 95, 148, 192, MAJ_FADE);
      case 0x3A:
        return get_color_chord( 63,  95, 172, MAJ_FADE);
      case 0x3B:
        return get_color_chord(  0,  87, 154, MAJ_FADE);
      case 0x3C:
        return get_color_chord( 13,  65, 104, MAJ_FADE);
      //
      // warmer
      //
      case 0x41:
        return get_color_chord( 20,  81,  25, MIN_FADE);
      case 0x42:
        return get_color_chord(  4,  87, 139, MIN_FADE);
      case 0x43:
        return get_color_chord(154,  37, 142, MIN_FADE);
      case 0x44:
        return get_color_chord(137,  40, 143, MIN_FADE);
      case 0x45:
        return get_color_chord(121,  43, 144, MIN_FADE);
      case 0x46:
        return get_color_chord(109,  34, 129, MIN_FADE);
      case 0x47:
        return get_color_chord(100,  27,  70, MIN_FADE);
      case 0x48:
        return get_color_chord(152, 105,  95, MIN_FADE);
      case 0x49:
        return get_color_chord(120,  76,  63, MIN_FADE);
      case 0x4A:
        return get_color_chord( 99,  63,  51, MIN_FADE);
      case 0x4B:
        return get_color_chord( 62,  48, 146, MIN_FADE);
      case 0x4C:
        return get_color_chord( 86,  46, 145, MIN_FADE);
    }
  }
}


void colorFade(int strip, uint32_t color, uint8_t wait) {
  int _px = 0;
  switch (strip) {
    case 0:
      _px = strip0.numPixels();
  }
  for (int i = 0; i < _px; i++) {
    switch (strip) {
      case 0:
        strip0.setPixelColor(i, color);
        strip0.show();
        break;
      case 1:
        strip1.setPixelColor(i, color);
        strip1.show();
        break;
      case 2:
        strip2.setPixelColor(i, color);
        strip2.show();
        break;
      case 3:
        strip3.setPixelColor(i, color);
        strip3.show();
        break;
    }
  }
  delay(wait);
}

void read_data() {
  if (Serial.available() > 0) {
    _byte = Serial.read();
    if (_byte > 0)
      _timer = 0;
  }
}

void loop() {
  _delay = 0;
  read_data();
  if (_timer > trigger) {
    rainbowCycle(0, 20);
//    rainbowCycle(1, 20);
//    rainbowCycle(2, 20);
//    rainbowCycle(3, 20);
    if (Serial.peek() > 0) {
      read_data();
    }
  }
  if (_timer < trigger) {
    uint32_t _color = get_color(_byte);
    colorFade(0, _color, _delay);
//    colorFade(1, _color, _delay);
//    colorFade(2, _color, _delay);
//    colorFade(3, _color, _delay);
  }
  if (_timer <= trigger) {
    _timer++;
  }
}

