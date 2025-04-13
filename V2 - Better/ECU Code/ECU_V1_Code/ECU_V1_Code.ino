// ECU V1 Code
// Jonathan Krueger
// WISP - 2025 - Half Badger

#include <Servo.h>
#include <Wire.h>

// Serial input command dictionary:

// System State Dictinoary:

// Sensor Config Information
// Sensor ID list:
// 103: command value - if applicable
// 102: time since last proper command
// 101: time since last state change
// 0: empty used to denote no sensor here
// 1-4: PT1-4
// 5-8: TC1-4
// 9-24: Extra Data1-16

// PT List, need to list Min, Max pressure, Min, Max Output, attatchment pins,
// names
float ptPressureRange[4][2] = {{0, 1000}, {0, 100}, {0, 100}, {0, 100}};
float ptOutputRange[4][2] = {{0.5, 4.5}, {0, 5}, {0, 5}, {0, 5}};
uint8_t ptPins[4] = {0, 1, 2, 3};
float ptValue[4] = {0.0, 0.0, 0.0, 0.0};
// char ptNames[4][12] = {"PT1", "PT2", "PT3", "PT4"};
uint8_t ptIds[4] = {0, 1, 2, 3};

// TC List, need to store TC Address, name, type
uint8_t tcAddress[4] = {0x61, 0x62, 0x63, 0x64};
// char tcNames[4][12] = {"TC1", "TC2", "TC3", "TC4"};
char tcType[4] = {'T', 'K', 'K', 'K'};
float tcHotValue[4] = {0.0, 0.0, 0.0, 0.0};
float tcColdValue[4] = {0.0, 0.0, 0.0, 0.0};
uint8_t tcIds[4] = {4, 5, 6, 7};

// Placeholders for additional data that any other system can pass in
// char extraDataNames[16][12] = {"-", "-", "-", "-", "-", "-", "-", "-", "-",
// "-", "-", "-"};
uint8_t extraDataIds[16] = {8,  9,  10, 11, 12, 13, 14, 15,
                            16, 17, 18, 19, 20, 21, 22, 23};
float extraDataValues[16] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};

// TC Registers
#define REG_HOT_JUNCTION_TEMP 0x00   // Hot Junction Temperature Register
#define REG_COLD_JUNCTION_TEMP 0x02  // Cold Junction Temperature Register
#define REG_THERMOCOUPLE_CFG 0x05    // Thermocouple Configuration Register

// Valve info
uint8_t valvePins[14] = {46, 6, 5, 4, 3, 2, 7, 8, 9, 10, 11, 12, 44, 45};
uint8_t valveState[14] = {0, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0};
uint8_t valveClosed[14] = {30, 50, 45, 45, 30, 30, 30,
                           30, 10, 15, 20, 45, 50, 40};
uint8_t valveOpened[14] = {160, 110, 110, 105, 105, 110, 125,
                           120, 120, 120, 100, 110, 110, 110};
uint8_t valveOvershoot[14] = {5, 5, 5, 5, 5, 5, 5, 10, 10, 10, 15, 15, 15};
uint8_t valveOverride[14] = {1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1};
Servo valveServos[14] = {};

// Task scheduling for valve adjustment info
#define MAX_TASKS 14  // Max number of scheduled tasks

struct ValveTask {
    unsigned long triggerTime;  // When to execute the adjustment (millis)
    int valveID;                // Which valve to adjust
    int position;               // Target position for the valve
    bool active;                // Whether the task is active
};

ValveTask tasks[MAX_TASKS];  // Task list

// State Tree info
#define NUM_STATES 50
#define STATE_CHANGES_PER_STATE 1
#define SENSORS_PER_STATE_CHANGE 3

// State numbers
uint8_t stateNumber[NUM_STATES] = {
    0, 1};  // Just numbering the states here for consistency and not having to
            // deal with index values

// STate numbers to move to
uint8_t stateToNumber[NUM_STATES][STATE_CHANGES_PER_STATE]
                     [SENSORS_PER_STATE_CHANGE] = {{{0}}, {{0}}};

// Defines each condition as either using > or < for the sensor threshold
// comparison
uint8_t
    stateChangeOperation[NUM_STATES][STATE_CHANGES_PER_STATE]
                        [SENSORS_PER_STATE_CHANGE] = {
                            {{2}},
                            {{2}}};  //[[0, 1, 2, 1]..] 0=sensor is < value, 1 =
                                     // sensor is = value, 2 = sensor is > value

// Defines the sensor ID value to be used in the comparision
uint8_t stateChangeSensorId[NUM_STATES][STATE_CHANGES_PER_STATE]
                           [SENSORS_PER_STATE_CHANGE] = {
                               {{101}}, {{101}}};  // Sensor ID to be used

// Defines the sensor threshold value to be considered
float stateChangeValue[NUM_STATES][STATE_CHANGES_PER_STATE]
                      [SENSORS_PER_STATE_CHANGE] = {{{10}},
                                                    {{5}}};  // Threshold value

// Defines how many sensors in each state change option need to be active to
// move. Can effectively be used to say all/or for conditions
uint8_t stateChangeNumSensors[NUM_STATES][STATE_CHANGES_PER_STATE] = {{1}, {1}};

// Defines what valves / pyro channels need to be open, 0 = closed / not firing,
// 1 = open / firing first 14 sets are the 14 valve indexes, last two are the
// 1st and 2nd pyro channels
uint8_t statePhysicalState[NUM_STATES][16] = {
    {0, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0}};

uint8_t pyro1 = 0;
uint8_t pyro2 = 0;

uint8_t pyro1Override = 0;
uint8_t pyro2Override = 0;

double pyro1Start = 0;
double pyro2Start = 0;

#define PYRO1_PIN 22
#define PYRO2_PIN 24

// Current time information
double t = 0.0;
double lastStateChangeTime = 0.0;
double lastSendTime = 0;
double lastRecieveTime = 0;

// Current state
uint8_t state = 0;

// Incoming messagse serial que
char partialCommand[100] = "";
int partialCommandIndex = 0;

void setup() {
    Serial.begin(115200);
    Wire.begin();

    // Configureing pinmodes for the PT sensors
    for (int i = 0; i < (sizeof(ptPins) / sizeof(ptPins[0])); i++) {
        pinMode(ptPins[i], INPUT);
    }

    // Configuring pinmode for battery sense signal
    pinMode(4, INPUT);
    pinMode(16, INPUT);

    // Config for the TCs
    for (int i = 0; i < (sizeof(tcAddress) / sizeof(tcAddress[0])); i++) {
        configureSensor(tcAddress[i], tcType[i]);
    }

    // Attaching servos to pins
    for (int i = 0; i < (sizeof(valvePins) / sizeof(valvePins[0])); i++) {
        pinMode(valvePins[i], OUTPUT);
        valveServos[i].attach(valvePins[i]);
    }

    // Servo task setup
    for (int i = 0; i < MAX_TASKS; i++) {
        tasks[i].active = false;
    }

    // Pyro setup
    pinMode(PYRO1_PIN, OUTPUT);
    pinMode(PYRO2_PIN, OUTPUT);
    digitalWrite(PYRO1_PIN, LOW);
    digitalWrite(PYRO2_PIN, LOW);
}

void loop() {
    double t = millis() / 1000.0;

    // Read for input commands
    //  '{' => start command
    //  '}' => end command
    char command[100] = "";
    int commandInt = 0;

    while (Serial.available()) {
        char nextChar = char(Serial.read());
        if (nextChar == '{') {
            partialCommand[0] = '{';
            partialCommandIndex = 1;
        } else if (nextChar == '}') {
            partialCommand[partialCommandIndex] = '}';

            for (int i = 0;
                 i < (sizeof(partialCommand) / sizeof(partialCommand[0]));
                 i++) {
                if (i <= partialCommandIndex) {
                    command[i] = partialCommand[i];
                } else {
                    command[i] = '_';
                }
            }

            commandInt = extractInt(command, 1);
            lastRecieveTime = t;
            partialCommandIndex = 0;
            break;
        } else {
            partialCommand[partialCommandIndex] = nextChar;

            partialCommandIndex += 1;
            if (partialCommandIndex > 63) {
                partialCommandIndex = 0;
            }
        }
    }

    if (command[0] == '{') {
        Serial.println(command);
    }

    // Execute on those commands - Move to new state w/ state config data,
    // update sensor config, update state tree, dump all data out Valve toggles,
    // 1: toggle valve directly, 2: sets manually override, eg {1,1} or {2,5}
    if (digitalRead(16) == HIGH) {
        commandInt = 1;
        command[0] = '{';
        command[1] = '1';
        command[2] = ',';
        command[3] = '7';
        command[4] = '}';
    }

    if (commandInt == 1) {
        int valveIndex = extractIntAfterNthComma(command, 0);
        // Serial.print("NEW VALVE STATE WHEW: ");
        // Serial.println(valveIndex);

        if (valveIndex >= 0 &&
            valveIndex <= 13) {  // Checking that the index is within range
            if (valveOverride[valveIndex] == 1 &&
                !isValveScheduled(valveIndex)) {  // Checking that this valve is
                                                  // in manual control
                if (valveState[valveIndex] == 1) {  // Gotta close it if open
                    valveServos[valveIndex].write(valveClosed[valveIndex] -
                                                  valveOvershoot[valveIndex]);
                    scheduleValveAdjustment(2, valveIndex, 0);
                    valveState[valveIndex] = 0;
                } else {  // Gotta open if if closed
                    valveServos[valveIndex].write(valveOpened[valveIndex] +
                                                  valveOvershoot[valveIndex]);
                    scheduleValveAdjustment(2, valveIndex, 1);
                    valveState[valveIndex] = 1;
                }
            }
        }
    }

    if (commandInt == 2) {
        int valveIndex = extractIntAfterNthComma(command, 0);

        if (valveIndex >= 0 &&
            valveIndex <= 13) {  // Checking that the index is within range
            if (valveOverride[valveIndex] == 0) {
                valveOverride[valveIndex] = 1;
            } else {
                valveOverride[valveIndex] = 0;
            }
        }
    }

    if (commandInt == 3) {
        int pyroIndex = extractIntAfterNthComma(command, 0);
        if (pyroIndex == 0 && pyro1Override == 1) {
            pyro1Start = t;
            pyro1 = 1;
        }

        else if (pyroIndex == 1 && pyro2Override == 1) {
            pyro2Start = t;
            pyro2 = 1;
        }
    }

    if (commandInt == 4) {
        int pyroIndex = extractIntAfterNthComma(command, 0);
        if (pyroIndex == 0) {
            pyro1Override = (pyro1Override == 1) ? 0 : 1;
        }

        else if (pyroIndex == 1) {
            pyro2Override = (pyro2Override == 1) ? 0 : 1;
        }
    }

    if (commandInt == 9) {
        int sN = extractIntAfterNthComma(command, 0);
        stateNumber[sN] = sN;

        stateChangeOperation[sN][0][0] = extractIntAfterNthComma(command, 1);
        stateChangeOperation[sN][0][1] = extractIntAfterNthComma(command, 2);
        stateChangeOperation[sN][0][2] = extractIntAfterNthComma(command, 3);

        stateChangeSensorId[sN][0][0] = extractIntAfterNthComma(command, 4);
        stateChangeSensorId[sN][0][1] = extractIntAfterNthComma(command, 5);
        stateChangeSensorId[sN][0][2] = extractIntAfterNthComma(command, 6);

        stateChangeValue[sN][0][0] = extractFloatAfterNthComma(command, 7);
        stateChangeValue[sN][0][1] = extractFloatAfterNthComma(command, 8);
        stateChangeValue[sN][0][2] = extractFloatAfterNthComma(command, 9);

        for (int valv = 0; valv < 16; valv++) {
            statePhysicalState[sN][valv] =
                extractIntAfterNthComma(command, 10 + valv);
        }

        stateToNumber[sN][0][0] = extractIntAfterNthComma(command, 26);
        stateToNumber[sN][0][1] = extractIntAfterNthComma(command, 27);
        stateToNumber[sN][0][2] = extractIntAfterNthComma(command, 28);
    }

    if (commandInt == 15) {
        state = 1;
        lastStateChangeTime = t;

        // Updating valve shit
        cancelValveAdjustments();
        for (int j = 0; j < (sizeof(statePhysicalState[1]) /
                             sizeof(statePhysicalState[1][0]));
             j++) {
            if (j < 14) {
                if (!valveOverride[j]) {
                    valveState[j] = statePhysicalState[1][j];
                }
            }
        }

        if (pyro1Override == 0) {
            pyro1 = statePhysicalState[1][14];
            pyro1Start = t;
        }
        if (pyro2Override == 0) {
            pyro2 = statePhysicalState[1][15];
            pyro2Start = t;
        }
    }

    // Read sensors
    // PT Read
    for (int i = 0; i < (sizeof(ptPins) / sizeof(ptPins[0])); i++) {
        ptValue[i] =
            (analogRead(ptPins[i]) / 1023.0 * 5.0 - ptOutputRange[i][0]) /
                (ptOutputRange[i][1] - ptOutputRange[i][0]) *
                (ptPressureRange[i][1] - ptPressureRange[i][0]) +
            ptPressureRange[i][0];
    }

    // TC Read
    for (int i = 0; i < (sizeof(tcAddress) / sizeof(tcAddress[0])); i++) {
        tcHotValue[i] = readTempRegister(tcAddress[i], REG_HOT_JUNCTION_TEMP);
        tcColdValue[i] = readTempRegister(tcAddress[i], REG_COLD_JUNCTION_TEMP);
    }

    // Battery sensor
    float batteryVoltage = analogRead(4) / 1023.0 * 5.0 * 2.0;

    // Evaluate if any state changes occur

    // Finding state index:
    int stateIndex = -1;
    for (int i = 0; i < (sizeof(stateNumber) / sizeof(stateNumber[0])); i++) {
        if (state == stateNumber[i]) {
            stateIndex = i;
            break;
        }
    }

    // Looping through each state change set, seeing if anything conditions
    // within them meet the threshold conditions
    for (int i = 0; i < (sizeof(stateChangeNumSensors[stateIndex]) /
                         sizeof(stateChangeNumSensors[stateIndex][0]));
         i++) {
        uint8_t thresholdValue = stateChangeNumSensors[stateIndex][i];
        uint8_t conditionsHit = 0;
        uint8_t toState = 511;
        for (int j = 0; j < (sizeof(stateChangeSensorId[stateIndex][i]) /
                             sizeof(stateChangeSensorId[stateIndex][i][0]));
             j++) {
            // Sensor id = 0, no condition here, just skip
            if (stateChangeSensorId[stateIndex][i][j] == 0) {
                continue;
            }
            // Sensor id = -1, time since last state change
            if (stateChangeSensorId[stateIndex][i][j] == 101) {
                // 0 => less than
                if (stateChangeOperation[stateIndex][i][j] == 0 &&
                    (t - lastStateChangeTime) <
                        stateChangeValue[stateIndex][i][j]) {
                    conditionsHit += 1;
                    toState = stateToNumber[stateIndex][i][j];
                }

                // 2 => greater than
                if (stateChangeOperation[stateIndex][i][j] == 2 &&
                    (t - lastStateChangeTime) >
                        stateChangeValue[stateIndex][i][j]) {
                    toState = stateToNumber[stateIndex][i][j];
                    conditionsHit += 1;
                }
            }
        }

        if (conditionsHit >= thresholdValue &&
            (thresholdValue > 0 ||
             (thresholdValue == 0 && conditionsHit > 0))) {
            uint8_t toStateIndex = -1;
            for (int k = 0; k < (sizeof(stateNumber) / sizeof(stateNumber[0]));
                 k++) {
                if (toState == stateNumber[k]) {
                    toStateIndex = k;
                    break;
                }
            }

            if (toStateIndex != -1) {
                state = toState;
                lastStateChangeTime = t;

                // Updating valve shit
                cancelValveAdjustments();
                for (int j = 0; j < (sizeof(statePhysicalState[stateIndex]) /
                                     sizeof(statePhysicalState[stateIndex][0]));
                     j++) {
                    if (j < 14) {
                        if (!valveOverride[j]) {
                            valveState[j] = statePhysicalState[toStateIndex][j];
                        }
                    }
                }

                if (pyro1Override == 0) {
                    pyro1 = statePhysicalState[toStateIndex][14];
                    pyro1Start = t;
                }
                if (pyro2Override == 0) {
                    pyro2 = statePhysicalState[toStateIndex][15];
                    pyro2Start = t;
                }
            }
        }
    }

    // Serial.println("======");
    // Serial.println(stateIndex);

    // Serial.println(tcHotValue[0]);

    // if(digitalRead(16) == HIGH){
    //   Serial.println("____----_");
    //   digitalWrite(24, HIGH);
    //   delay(1000);
    //   digitalWrite(24, LOW);
    // }

    // Processing valve
    checkValveAdjustments();
    for (int i = 0; i < (sizeof(valvePins) / sizeof(valvePins[0])); i++) {
        if (!isValveScheduled(i)) {
            if (valveState[i] == 1) {
                valveServos[i].write(valveOpened[i]);
            } else {
                valveServos[i].write(valveClosed[i]);
            }
        }
    }

    // Processign pyro channels
    // Disabling if they've been on for more than 1s
    if ((t - pyro1Start) > 0.75 && pyro1 == 1) {
        pyro1 = 0;
    }

    if ((t - pyro2Start) > 0.75 && pyro2 == 1) {
        pyro2 = 0;
    }

    if (pyro1 == 1) {
        digitalWrite(PYRO1_PIN, HIGH);
    } else {
        digitalWrite(PYRO1_PIN, LOW);
    }

    if (pyro2 == 1) {
        digitalWrite(PYRO2_PIN, HIGH);
    } else {
        digitalWrite(PYRO2_PIN, LOW);
    }

    if ((millis() / 1000.0) - lastSendTime > 0.5) {
        printValveStates();
        printValveOverrideStates();
        printPyroStates();

        // Battery Voltage
        Serial.print("{9,");
        Serial.print(batteryVoltage);
        Serial.println("}");

        // Current state
        Serial.print("{8,");
        Serial.print(state);
        Serial.println("}");

        // Time since last command
        Serial.print("{7,");
        Serial.print(t - lastRecieveTime);
        Serial.println("}");

        // Time since last state change
        Serial.print("{6,");
        Serial.print(t - lastStateChangeTime);
        Serial.println("}");

        lastSendTime = millis() / 1000.0;
    }

    delay(20);
}

// Configure thermocouple wtih type
void configureSensor(uint8_t addr, char type) {
    writeRegister(addr, REG_THERMOCOUPLE_CFG, getTCCode(type));
    // Serial.print("Set sensor at 0x");
    // Serial.print(addr, HEX);
    // Serial.print(" to Type: ");
    // Serial.println(type);
}

// Convert tc char to hex
uint8_t getTCCode(char type) {
    switch (type) {
        case 'K':
            return 0x00;
        case 'J':
            return 0x01;
        case 'T':
            return 0x02;
        case 'N':
            return 0x03;
        case 'S':
            return 0x04;
        case 'E':
            return 0x05;
        case 'B':
            return 0x06;
        case 'R':
            return 0x07;
        default:
            return 0xFF;  // Invalid type
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

float extractFloat(const char str[], int i) {
    if (str[i] == '\0') return -9999;  // Ensure index is within bounds

    char tempBuffer[20];  // Buffer to hold extracted number
    int j = 0;

    // Extract the number into tempBuffer
    while (str[i] != '\0' && j < 19) {
        if (isdigit(str[i]) || str[i] == '.' || str[i] == '-') {
            tempBuffer[j++] = str[i];
        } else if (j > 0) {
            break;  // Stop when we hit a non-numeric character after
                    // starting
        }
        i++;
    }
    tempBuffer[j] = '\0';  // Null-terminate the extracted string

    // Convert to float
    if (j == 0) return -9999;  // No valid number found
    return atof(tempBuffer);
}

int extractInt(const char str[], int i) {
    if (str[i] == '\0') return -9999;  // Ensure index is within bounds

    char tempBuffer[8];  // Buffer to hold extracted number
    int j = 0;

    // Extract the number into tempBuffer
    while (str[i] != '\0' && j < 7) {
        if (isdigit(str[i]) || str[i] == '-') {
            tempBuffer[j++] = str[i];
        } else if (j > 0) {
            break;  // Stop when we hit a non-numeric character after
                    // starting
        }
        i++;
    }
    tempBuffer[j] = '\0';  // Null-terminate the extracted string

    // Convert to int
    if (j == 0) return -9999;  // No valid number found
    return atoi(tempBuffer);
}

int extractIntAfterNthComma(const char str[], int n) {
    int len = strlen(str);
    if (len < 5) {
        return -9999;  // Invalid format
    }

    int commaCount = 0;
    int targetIndex = -1;

    // Find the nth comma
    for (int i = 1; i < len - 1; i++) {  // Ignore first '{' and last '}'
        if (str[i] == ',') {
            if (commaCount == n) {
                targetIndex = i + 1;  // The number starts after this comma
                break;
            }
            commaCount++;
        }
    }

    if (targetIndex == -1) return -9999;  // nth comma not found

    // Extract integer after the nth comma using extractInt function
    return extractInt(str, targetIndex);
}

float extractFloatAfterNthComma(const char str[], int n) {
    int len = strlen(str);
    if (len < 5) {
        return -9999;  // Invalid format
    }

    int commaCount = 0;
    int targetIndex = -1;

    // Find the nth comma
    for (int i = 1; i < len - 1; i++) {  // Ignore first '{' and last '}'
        if (str[i] == ',') {
            if (commaCount == n) {
                targetIndex = i + 1;  // The number starts after this comma
                break;
            }
            commaCount++;
        }
    }

    if (targetIndex == -1) return -9999;  // nth comma not found

    // Extract integer after the nth comma using extractInt function
    return extractFloat(str, targetIndex);
}

// Function to schedule a valve adjustment
void scheduleValveAdjustment(unsigned long delaySeconds, int valveID,
                             int position) {
    for (int i = 0; i < MAX_TASKS; i++) {
        if (!tasks[i].active) {  // Find an empty slot
            tasks[i].triggerTime = millis() + (delaySeconds * 1000);
            tasks[i].valveID = valveID;
            tasks[i].position = position;
            tasks[i].active = true;
            // Serial.print("Scheduled Valve ");
            // Serial.print(valveID);
            // Serial.print(" adjustment to ");
            // Serial.print(position);
            // Serial.print("% in ");
            // Serial.print(delaySeconds);
            // Serial.println(" seconds.");
            return;
        }
    }
    // Serial.println("Task list full! Cannot schedule new valve
    // adjustment.");
}

// Function to check and execute scheduled valve adjustments
void checkValveAdjustments() {
    unsigned long currentTime = millis();
    for (int i = 0; i < MAX_TASKS; i++) {
        if (tasks[i].active && currentTime >= tasks[i].triggerTime) {
            if (tasks[i].position == 0) {
                valveServos[tasks[i].valveID].write(
                    valveClosed[tasks[i].valveID]);
                // Serial.println("Adjust Closed");
            } else {
                valveServos[tasks[i].valveID].write(
                    valveOpened[tasks[i].valveID]);
                // Serial.println("Adjust open");
            }

            tasks[i].active = false;  // Mark task as completed
        }
    }
}

// Mark all tasks of valve adjustment as complete
void cancelValveAdjustments() {
    for (int i = 0; i < MAX_TASKS; i++) {
        tasks[i].active = false;
    }
}

bool isValveScheduled(int valveID) {
    for (int i = 0; i < MAX_TASKS; i++) {
        if (tasks[i].active && tasks[i].valveID == valveID) {
            return true;  // Found an active task for this valve
        }
    }
    return false;  // No active task for this valve
}

void printValveStates() {
    Serial.print("{1");
    for (int i = 0; i < 14; i++) {
        Serial.print(",");
        Serial.print(valveState[i]);
    }
    Serial.println("}");
}

void printValveOverrideStates() {
    Serial.print("{2");
    for (int i = 0; i < 14; i++) {
        Serial.print(",");
        Serial.print(valveOverride[i]);
    }
    Serial.println("}");
}

void printPyroStates() {
    Serial.print("{3,");
    Serial.print(pyro1);
    Serial.print(",");
    Serial.print(pyro2);
    Serial.print(",");
    Serial.print(pyro1Override);
    Serial.print(",");
    Serial.print(pyro2Override);
    Serial.println("}");
}