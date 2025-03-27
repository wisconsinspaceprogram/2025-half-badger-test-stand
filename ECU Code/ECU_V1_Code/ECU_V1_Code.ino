// ECU V1 Code
// Jonathan Krueger
// WISP - 2025 - Half Badger

#include <Wire.h>

// Serial input command dictionary:

// System State Dictinoary:

// Sensor Config Information
// Sensor ID list:
// -1: time since last state change
// 0-3: PT1-4
// 4-7: TC1-4

// PT List, need to list Min, Max pressure, Min, Max Output, attatchment pins, names
float ptPressureRange[4][2] = {{0, 1000}, {0, 100}, {0, 100}, {0, 100}};
float ptOutputRange[4][2] = {{0.5, 4.5}, {0, 5}, {0, 5}, {0, 5}};
int ptPins[4] = {0, 1, 2, 3};
float ptValue[4] = {0.0, 0.0, 0.0, 0.0};
char ptNames[4][12] = {"PT1", "PT2", "PT3", "PT4"};
int ptIds[4] = {0, 1, 2, 3};

// TC List, need to store TC Address, name, type
uint8_t tcAddress[4] = {0x61, 0x62, 0x63, 0x64};
char tcNames[4][12] = {"TC1", "TC2", "TC3", "TC4"};
char tcType[4] = {'T', 'K', 'K', 'K'};
float tcHotValue[4] = {0.0, 0.0, 0.0, 0.0};
float tcColdValue[4] = {0.0, 0.0, 0.0, 0.0};
int tcIds[4] = {4, 5, 6, 7};

// Placeholders for additional data that any other system can pass in
int extraDataIds[16] = {8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23};
float extraDataValues[16] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};

// Registers
#define REG_HOT_JUNCTION_TEMP 0x00  // Hot Junction Temperature Register
#define REG_COLD_JUNCTION_TEMP 0x02 // Cold Junction Temperature Register
#define REG_THERMOCOUPLE_CFG   0x05 // Thermocouple Configuration Register

// State Tree info
#define NUM_STATES 100
#define STATE_CHANGES_PER_STATE 3
#define SENSORS_PER_STATE_CHANGE 6

// State numbers
int stateNumber[NUM_STATES] = {0, 1};  //Just numbering the states here for consistency and not having to deal with index values

// Defines each condition as either using > or < for the sensor threshold comparison
int stateChangeOperation[NUM_STATES][STATE_CHANGES_PER_STATE][SENSORS_PER_STATE_CHANGE] = {{{1}}, {{-1}}}; //[[-1, 1, 1, 1]..] 1=sensor is > value, -1 = sensor is < value

// Defines the sensor ID value to be used in the comparision
int stateChangeSensorId[NUM_STATES][STATE_CHANGES_PER_STATE][SENSORS_PER_STATE_CHANGE] = {{{4}}, {{4}}};  // Sensor ID to be used

// Defines the sensor threshold value to be considered
float stateChangeValue[NUM_STATES][STATE_CHANGES_PER_STATE][SENSORS_PER_STATE_CHANGE] = {{{28}}, {{26}}}; // Threshold value

// Defines how many sensors in each state change option need to be active to move. Can effectively be used to say all/or for conditions
int stateChangeNumSensors[NUM_STATES][STATE_CHANGES_PER_STATE] = {{1, 0, 0}, {1, 0, 0}};

//Current time information
double t = 0.0;
double lastStateChange = 0.0;

//Current state
int state = 0;



void setup() {
  Serial.begin(115200);
  Wire.begin();

  //Configureing pinmodes for the PT sensors
  for(int i = 0; i < (sizeof(ptPins) / sizeof(ptPins[0])); i++){
    pinMode(ptPins[i], INPUT);
  }

  //Configuring pinmode for battery sense signal
  pinMode(4, INPUT);

  //Config for the TCs
  for(int i = 0; i < (sizeof(tcAddress) / sizeof(tcAddress[0])); i++){
    configureSensor(tcAddress[i], tcType[i]);
  }

  Serial.println("Start");

}





void loop() {
  //Read for input commands

  //Execute on those commands - Move to new state w/ state config data, update sensor config, update state tree, dump all data out

  //Read sensors 
  //PT Read
  for(int i = 0; i < (sizeof(ptPins) / sizeof(ptPins[0])); i++){
   ptValue[i] = (analogRead(ptPins[i]) / 1023.0 * 5.0 - ptOutputRange[i][0]) / (ptOutputRange[i][1] - ptOutputRange[i][0]) * (ptPressureRange[i][1] - ptPressureRange[i][0]) + ptPressureRange[i][0];
  }

  // TC Read
  for(int i = 0; i < (sizeof(tcAddress) / sizeof(tcAddress[0])); i++){
   tcHotValue[i] = readTempRegister(tcAddress[i], REG_HOT_JUNCTION_TEMP);
   tcColdValue[i] = readTempRegister(tcAddress[i], REG_COLD_JUNCTION_TEMP);
  }

  //Battery sensor
  float batteryVoltage = analogRead(4)/1023.0*5.0*2.0;

  // Evaluate if any state changes occur
  Serial.println(tcHotValue[0]);

  delay(100);
}




// Configure thermocouple wtih type
void configureSensor(uint8_t addr, char type) {
    writeRegister(addr, REG_THERMOCOUPLE_CFG, getTCCode(type));
    Serial.print("Set sensor at 0x");
    Serial.print(addr, HEX);
    Serial.print(" to Type: ");
    Serial.println(type);
}

// Convert tc char to hex
uint8_t getTCCode(char type) {
    switch (type) {
        case 'K': return 0x00;
        case 'J': return 0x01;
        case 'T': return 0x02;
        case 'N': return 0x03;
        case 'S': return 0x04;
        case 'E': return 0x05;
        case 'B': return 0x06;
        case 'R': return 0x07;
        default:  return 0xFF;  // Invalid type
    }
}

// Write registers from TC chips
void writeRegister(uint8_t addr, uint8_t reg, uint8_t value) {
    Wire.beginTransmission(addr);
    Wire.write(reg);
    Wire.write(value);
    Wire.endTransmission();
}

// Read registers from TC chips
float readTempRegister(uint8_t addr, uint8_t reg) {
    Wire.beginTransmission(addr);
    Wire.write(reg);
    Wire.endTransmission();
    
    Wire.requestFrom(addr, (uint8_t)2);
    if (Wire.available() < 2) {
        return NAN;  // Return NaN if no response
    }

    int16_t rawData = (Wire.read() << 8) | Wire.read();
    
    return rawData * 0.0625;  // Convert raw data to temperature in °C
}

