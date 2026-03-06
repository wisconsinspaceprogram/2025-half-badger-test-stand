/*
  ECU_Code.ino

  Command protocol (from PC -> Mega over Serial):
    Command is framed by braces: {AA,XX,D...D(optional)}
      AA = address (0-11 local servo valves, 12+ RS485 valve address, pyro uses 0/1)
      XX = command
        1 = open valve (local if AA 0-11, RS485 if AA>=12)
        2 = close valve (local if AA 0-11, RS485 if AA>=12)
        3 = fire pyro (AA=0 -> pyro1, AA=1 -> pyro2)
        4 = relay raw payload to RS485 (strip AA,XX and forward rest inside braces)
        5 = query RS485 valve angles
        6 = start hardcoded sequence (AA = burn duration in seconds)

  Telemetry (Mega -> PC over Serial), unchanged formats:
    {1, <12 local desired states>, <12 rs485 desired states>}
    {2, <12 local actual states from !limitSwitch>, <12 rs485 actual states from angle>}
    {3, <batteryVoltage>}
    {4, <12 rs485 "percentages" = angle - 50>}
    {5, <sequenceState>, <currentStepIndex>, <stepElapsedTime>}
      States: 0=IDLE, 1=STARTUP, 2=BURN, 3=SHUTDOWN
*/

#include <Servo.h>
#include <MemoryFree.h>
#include <ctype.h>
#include <string.h>
#include <stdio.h>

// ----------------------- Constants / Config -----------------------

static const uint8_t N_LOCAL_VALVES = 12;
static const uint8_t N_RS485_VALVES = 12;

#define PYRO1_PIN 22
#define PYRO2_PIN 24

// Profiles
struct ValveProfile {
  int open;
  int mostlyClosed;
  int closed;
  int closeBackoff;
  int openBackoff;
  float openBackoffDelay_s;
  float closeBackoffDelay_s;
};

static const ValveProfile NONCRYO = {
  /*open*/ 10,
  /*mostlyClosed*/ 75,
  /*closed*/ 130,
  /*closeBackoff*/ 8,
  /*openBackoff*/ 5,
  /*openBackoffDelay_s*/ 2.0,
  /*closeBackoffDelay_s*/ 0.5
};

static const ValveProfile CRYO = {
  /*open*/ 160,
  /*mostlyClosed*/ 50,
  /*closed*/ 10,
  /*closeBackoff*/ 2,
  /*openBackoff*/ 2,
  /*openBackoffDelay_s*/ 2.5,
  /*closeBackoffDelay_s*/ 0.5
};

// ----------------------- Sequence System -----------------------

enum SequenceState {
  SEQ_IDLE = 0,
  SEQ_STARTUP = 1,
  SEQ_BURN = 2,
  SEQ_SHUTDOWN = 3
  SEQ_ABORT = 4
};

struct SequenceStep {
  float time_s;        // Time from previous step (or sequence start for first step)
  uint8_t valve;       // Valve index (0-11 local, 12+ RS485)
  uint8_t action;      // 1=open, 2=close, 3=pyro fire, 4=wait for burn duration
};

// ===== HOTFIRE SEQUENCE =====
// Use action=4 to insert a wait for the burn duration sent from computer
SequenceStep hotfireSequence[] = {
  // Startup phase
  {0.0, poll},     // NEED TO DEFINE A POLL ACTION
  {1.0, 12, 1},     // Open LOX Purge
  {0.0, 13, 1},     // Open IPA Purge
  {1.0, poll},
  {2.0, 13, 2},     // Close IPA Purge
  {0.5, 0, 3},      // Fire pyro 0
  {0.5, poll},
  {0.5,17, 1},     // Open IPA Main
  {0.25, 4, 1},     // Open LOX Main
  {0.0, 12, 2},     // Close LOX Purge
  {0.5, poll},
  {burnDuration_s, 0, 4},  // Wait for burn duration
  {0.0, 4, 2},     // Close LOX Main
  {0.0, 12, 1},     // Open LOX Purge
  {0.5, poll},
  {0.5, 17, 2},     // Close IPA Main
  {0.0, 13, 1},     // Open IPA Purge
  {2.0, poll},
  {8.0, 14, 2},     // Close GN2 Main
  {1.0, 13, 2},     // Close IPA Purge
  {0.0, 12, 2},     // Close LOX Purge
  {1.0, poll},
  {4.0, 15, 1},     // Open IPA Tank Vent
  {0.0, 1,  1},     // Open LOX Tank Vent
  {1.0, poll}
};

  
  // Burn duration wait
  {0.0, 0, 4},      // Wait for burn duration (valve field unused)
  
  // Shutdown phase
  
};

static const int HOTFIRE_SEQ_LENGTH = sizeof(hotfireSequence) / sizeof(hotfireSequence[0]);

// Sequence state variables
SequenceState sequenceState = SEQ_IDLE;
float lastStepTime_s = 0.0f;
float burnWaitStartTime_s = 0.0f;
int currentStepIndex = 0;
float burnDuration_s = 0.0f;

// ----------------------- Valve Structs -----------------------

struct ValveConfig {
  uint8_t servoPin;
  uint8_t limitSwitchPin;
  bool isCryo;
};

struct ValveState {
  uint8_t desiredOpen;           // 0=closed, 1=open (same meaning as original valveStates[])
  float angle;                   // last commanded angle (same meaning as original valveAngle[])
  bool closing;                  // actively closing toward limit/closed (same meaning as valveClosing[])
  bool needsOpenBackoff;         // same meaning as needsOpeningBackoff[]
  bool needsCloseBackoff;        // same meaning as needsClosingBackoff[]
  float lastOpenCommand_s;       // same meaning as lastOpeningCommand[]
  float lastCloseCommand_s;      // same meaning as lastClosingCommand[]
  Servo servo;
};

// Original pin maps / cryo flags
static const ValveConfig VALVE_CFG[N_LOCAL_VALVES] = {
  /*0*/  {13, 27, true},
  /*1*/  { 2, 29, true},
  /*2*/  { 3, 31, true},
  /*3*/  { 4, 33, true},
  /*4*/  { 5, 35, true},
  /*5*/  { 6, 37, true},
  /*6*/  { 7, 39, true},
  /*7*/  { 8, 41, true},
  /*8*/  { 9, 43, true},
  /*9*/  {10, 45, true},
  /*10*/ {11, 47, true},
  /*11*/ {12, 49, false}
};

static ValveState valves[N_LOCAL_VALVES];

// ----------------------- RS485 Valves -----------------------

uint8_t rs485ValveAddresses[N_RS485_VALVES]     = { 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23 };
uint8_t rs485ValveAngles[N_RS485_VALVES]        = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 };
uint8_t rs485ValveDesiredStates[N_RS485_VALVES] = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 };

// ----------------------- Pyros -----------------------

uint8_t pyro1 = 0;
uint8_t pyro2 = 0;
double pyro1Start_s = 0;
double pyro2Start_s = 0;

// ----------------------- Telemetry Timing -----------------------

float lastValveStatePrint_s = 0.0f;

// ----------------------- Serial Command Buffer -----------------------

char partialCommand[100] = "";
int partialCommandIndex = 0;

// ----------------------- Helpers -------------------------

int indexOfNthComma(const char str[], int n);
int extractInt(const char str[], int i);
int extractIntAfterNthComma(const char str[], int n);
float extractFloat(const char str[], int i);
float extractFloatAfterNthComma(const char str[], int n);

// ----------------------- Forward Declarations -----------------------

static inline const ValveProfile& profileFor(uint8_t i) {
  return VALVE_CFG[i].isCryo ? CRYO : NONCRYO;
}

void startOpenValve(uint8_t i, float t_s);
void startCloseValve(uint8_t i, float t_s);
void updateLocalValves(float t_s);

void updateRS485ValveAngles();
void printDesiredValveStates();
void printActualValveStates();
void printRS485ValvePercentages();
void executeSequenceStep(const SequenceStep& step, float t_s);
void updateSequence(float t_s);
void printSequenceStatus();

// ----------------------- Setup -----------------------

void setup() {
  Serial.begin(115200);

  // RS485 bus on Serial3
  Serial3.begin(115200);
  Serial3.setTimeout(10);

  pinMode(A4, INPUT);

  // Initialize local valves
  for (uint8_t i = 0; i < N_LOCAL_VALVES; i++) {
    pinMode(VALVE_CFG[i].servoPin, OUTPUT);
    pinMode(VALVE_CFG[i].limitSwitchPin, INPUT);

    valves[i].desiredOpen = 0;
    valves[i].closing = false;
    valves[i].needsOpenBackoff = false;
    valves[i].needsCloseBackoff = false;
    valves[i].lastOpenCommand_s = 0.0f;
    valves[i].lastCloseCommand_s = 0.0f;

    valves[i].servo.attach(VALVE_CFG[i].servoPin);

    const ValveProfile& P = profileFor(i);
    valves[i].servo.write(P.mostlyClosed);
    valves[i].angle = (float)P.mostlyClosed;
  }

  // Misc output pin for indicator/relay
  pinMode(46, OUTPUT);

  // Pyro setup
  pinMode(PYRO1_PIN, OUTPUT);
  pinMode(PYRO2_PIN, OUTPUT);
  digitalWrite(PYRO1_PIN, LOW);
  digitalWrite(PYRO2_PIN, LOW);
}

// ----------------------- Loop -----------------------

void loop() {
  float t_s = millis() / 1000.0f;

  // -------- Receive one command (if available) --------
  char command[100] = "";
  int commandInt = 0;
  int commandAddress = 0;
  int commandEndIndex = 0;

  // Same framing behavior: build between '{' and '}', parse on '}'
  while (Serial.available()) {
    char nextChar = (char)Serial.read();

    if (nextChar == '{') {
      partialCommand[0] = '{';
      partialCommandIndex = 1;
    } else if (nextChar == '}') {
      commandEndIndex = partialCommandIndex;
      partialCommand[partialCommandIndex] = '}';

      // Copy into command 
      for (int i = 0; i < (int)(sizeof(partialCommand) / sizeof(partialCommand[0])); i++) {
        if (i <= partialCommandIndex) command[i] = partialCommand[i];
        else command[i] = '_';
      }

      commandInt = extractIntAfterNthComma(command, 0);     // after first comma
      commandAddress = extractIntAfterNthComma(command, -1); // first int after '{'

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

  // -------- Command Handling  --------

  // 1 = open valve
  if (commandInt == 1) {
    int valveIndex = commandAddress;

    // Local servo valve
    if (valveIndex >= 0 && valveIndex <= 11) {
      startOpenValve((uint8_t)valveIndex, t_s);
    }

    // RS485 valve 
    if (valveIndex >= 12) {
      int valveAddress = commandAddress;

      char buffer[10];
      sprintf(buffer, "{%02d,01}", valveAddress);
      Serial3.println(buffer);

      rs485ValveDesiredStates[valveIndex - 12] = 1;
    }
  }

  // 2 = close valve
  if (commandInt == 2) {
    int valveIndex = commandAddress;

    // Local servo valve
    if (valveIndex >= 0 && valveIndex <= 11) {
      startCloseValve((uint8_t)valveIndex, t_s);
    }

    // RS485 valve
    if (valveIndex >= 12) {
      int valveAddress = commandAddress;

      char buffer[10];
      sprintf(buffer, "{%02d,02}", valveAddress);
      Serial3.println(buffer);

      rs485ValveDesiredStates[valveIndex - 12] = 0;
    }
  }

  // 3 = fire pyro
  if (commandInt == 3) {
    int pyroIndex = commandAddress;
    if (pyroIndex == 0) {
      pyro1Start_s = t_s;
      pyro1 = 1;
    } else if (pyroIndex == 1) {
      pyro2Start_s = t_s;
      pyro2 = 1;
    }
  }

  // 4 = relay to RS485: forward everything after AA,XX
  if (commandInt == 4) {
    int indexOfSecondComma = indexOfNthComma(command, 1);

    Serial3.print("{");
    for (int i = indexOfSecondComma + 1; i <= commandEndIndex && command[i] != '\0'; i++) {
      Serial3.print(command[i]);
    }
    Serial3.println();
  }

  // 5 = query RS485 angles
  if (commandInt == 5) {
    updateRS485ValveAngles();
  }

  // 6 = start hardcoded sequence with burn duration
  if (commandInt == 6) {
    float burnDur = extractFloatAfterNthComma(command, 1);
    if (burnDur > 0 && sequenceState == SEQ_IDLE) {
      burnDuration_s = burnDur;
      sequenceState = SEQ_STARTUP;
      lastStepTime_s = t_s;
      currentStepIndex = 0;
      
      // Send confirmation
      Serial.print("{5,STARTING,");
      Serial.print(burnDuration_s);
      Serial.println("}");
    }
  }

  // -------- Pyro processing (0.75s pulse) --------
  if ((t_s - pyro1Start_s) > 0.75f && pyro1 == 1) pyro1 = 0;
  if ((t_s - pyro2Start_s) > 0.75f && pyro2 == 1) pyro2 = 0;

  digitalWrite(PYRO1_PIN, pyro1 ? HIGH : LOW);
  digitalWrite(PYRO2_PIN, pyro2 ? HIGH : LOW);

  // -------- Local valve update + backoffs  --------
  updateLocalValves(t_s);

  // -------- Hardcoded Sequence Execution --------
  updateSequence(t_s);

  // Keep your original pacing
  delay(20);

  // -------- Battery sensor  --------
  float batteryVoltage = analogRead(4) / 1023.0f * 5.0f * 2.0f;

  // -------- Telemetry at ~4 Hz --------
  if ((t_s - lastValveStatePrint_s) > 0.25f) {
    printDesiredValveStates();
    printActualValveStates();

    Serial.print("{3,");
    Serial.print(batteryVoltage);
    Serial.println("}");

    printRS485ValvePercentages();
    printSequenceStatus();

    lastValveStatePrint_s = t_s;
  }

  // indicator behavior 
  digitalWrite(46, valves[0].desiredOpen);
}

// ----------------------- Local Valve Functions -----------------------

void startOpenValve(uint8_t i, float t_s) {
  if (i >= N_LOCAL_VALVES) return;

  // Only act on a transition from closed->open
  if (valves[i].desiredOpen == 0) {
    valves[i].desiredOpen = 1;

    const ValveProfile& P = profileFor(i);

    if (VALVE_CFG[i].isCryo) {
      valves[i].angle = (float)(P.open + P.openBackoff);
      valves[i].servo.write(P.open + P.openBackoff);
    } else {
      valves[i].angle = (float)(P.open - P.openBackoff);
      valves[i].servo.write(P.open - P.openBackoff);
    }

    valves[i].closing = false;
    valves[i].needsCloseBackoff = false;
    valves[i].needsOpenBackoff = true;
    valves[i].lastOpenCommand_s = t_s;
  }
}

void startCloseValve(uint8_t i, float t_s) {
  if (i >= N_LOCAL_VALVES) return;

  // Only act on a transition from open->closed
  if (valves[i].desiredOpen == 1) {
    valves[i].desiredOpen = 0;

    const ValveProfile& P = profileFor(i);

    valves[i].servo.write(P.mostlyClosed);
    valves[i].angle = (float)P.mostlyClosed;

    valves[i].closing = true;
    valves[i].needsOpenBackoff = false;
    valves[i].lastCloseCommand_s = t_s;
  }
}

void updateLocalValves(float t_s) {
  for (uint8_t i = 0; i < N_LOCAL_VALVES; i++) {
    const ValveProfile& P = profileFor(i);

    // Open backoff delay -> final open
    if (valves[i].needsOpenBackoff &&
        (t_s - valves[i].lastOpenCommand_s) > P.openBackoffDelay_s) {
      valves[i].needsOpenBackoff = false;
      valves[i].servo.write(P.open);
      valves[i].angle = (float)P.open;
    }

    // Close backoff delay -> relieve torque after seating
    if (valves[i].needsCloseBackoff &&
        (t_s - valves[i].lastCloseCommand_s) > P.closeBackoffDelay_s) {
      valves[i].needsCloseBackoff = false;

      if (VALVE_CFG[i].isCryo) {
        valves[i].servo.write((int)(valves[i].angle + P.closeBackoff));
        valves[i].angle = valves[i].angle + (float)P.closeBackoff;
      } else {
        valves[i].servo.write((int)(valves[i].angle - P.closeBackoff));
        valves[i].angle = valves[i].angle - (float)P.closeBackoff;
      }
    }

    // Closing motion toward limit
    if (valves[i].closing) {
      bool limitHit = (digitalRead(VALVE_CFG[i].limitSwitchPin) == 1);
      bool angleStop = VALVE_CFG[i].isCryo ? (valves[i].angle < P.closed) : (valves[i].angle > P.closed);

      if (limitHit || angleStop) {
        valves[i].closing = false;

        valves[i].needsCloseBackoff = true;
        valves[i].lastCloseCommand_s = t_s;
      } else if ((t_s - valves[i].lastCloseCommand_s) > 0.5f) {
        // after 0.5s, every loop iteration steps by 0.5
        if (VALVE_CFG[i].isCryo) {
          valves[i].servo.write((int)(valves[i].angle - 0.5f));
          valves[i].angle = valves[i].angle - 0.5f;
        } else {
          valves[i].servo.write((int)(valves[i].angle + 0.5f));
          valves[i].angle = valves[i].angle + 0.5f;
        }
      }
    }
  }
}

// ----------------------- RS485 Query (unchanged) -----------------------

void updateRS485ValveAngles() {
  char buf[40];
  char cmd[16];

  for (int i = 0; i < 12; i++) {
    int addr = rs485ValveAddresses[i];
    sprintf(cmd, "{%02d,32}", addr);

    // Flush leftover bytes
    while (Serial3.available()) Serial3.read();

    // Send query
    Serial3.print(cmd);
    Serial3.flush();

    // Wait briefly for start of reply
    unsigned long start = millis();
    while (!Serial3.available() && (millis() - start) < 3) {
      delayMicroseconds(200);
    }

    int len = Serial3.readBytesUntil('}', buf, sizeof(buf) - 1);
    buf[len] = '}';
    buf[len + 1] = '\0';

    int v = -1, angle = -1;
    if (sscanf(buf, "{v,%d,%d}", &v, &angle) == 2) {
      rs485ValveAngles[v - 12] = angle;
    }

    delay(2);
  }
}

// ----------------------- Telemetry Prints (unchanged formats) -----------------------

void printDesiredValveStates() {
  Serial.print("{1");
  for (uint8_t i = 0; i < N_LOCAL_VALVES; i++) {
    Serial.print(",");
    Serial.print(valves[i].desiredOpen);
  }

  for (uint8_t i = 0; i < N_RS485_VALVES; i++) {
    Serial.print(",");
    Serial.print(rs485ValveDesiredStates[i]);
  }

  Serial.println("}");
}

void printActualValveStates() {
  Serial.print("{2");
  for (uint8_t i = 0; i < N_LOCAL_VALVES; i++) {
    Serial.print(",");
    Serial.print(!digitalRead(VALVE_CFG[i].limitSwitchPin));
  }

  for (uint8_t i = 0; i < N_RS485_VALVES; i++) {
    Serial.print(",");
    uint8_t angle = rs485ValveAngles[i];
    if (angle > 30 && angle < 80) Serial.print("0");  // Closed
    else Serial.print("1");                           // Open
  }

  Serial.println("}");
}

void printRS485ValvePercentages() {
  Serial.print("{4");
  for (uint8_t i = 0; i < N_RS485_VALVES; i++) {
    Serial.print(",");
    uint8_t angle = rs485ValveAngles[i];
    int percent = (int)angle - 50;
    Serial.print(percent);
  }
  Serial.println("}");
}

// ----------------------- Parsing Helpers (same as original) -----------------------

int extractInt(const char str[], int i) {
  if (str[i] == '\0') return -9999;

  char tempBuffer[8];
  int j = 0;

  while (str[i] != '\0' && j < 7) {
    if (isdigit(str[i]) || str[i] == '-') {
      tempBuffer[j++] = str[i];
    } else if (j > 0) {
      break;
    }
    i++;
  }
  tempBuffer[j] = '\0';

  if (j == 0) return -9999;
  return atoi(tempBuffer);
}

int extractIntAfterNthComma(const char str[], int n) {
  int len = (int)strlen(str);
  if (len < 5) return -9999;

  if (n == -1) {
    return extractInt(str, 1);
  }

  int targetIndex = indexOfNthComma(str, n) + 1;
  if (targetIndex == -1) return -9999;

  return extractInt(str, targetIndex);
}

int indexOfNthComma(const char str[], int n) {
  int commaCount = 0;
  int targetIndex = -1;

  for (int i = 1; i < (int)strlen(str) - 1; i++) {
    if (str[i] == ',') {
      if (commaCount == n) {
        targetIndex = i;
        break;
      }
      commaCount++;
    }
  }
  return targetIndex;
}

float extractFloatAfterNthComma(const char str[], int n) {
  int len = (int)strlen(str);
  if (len < 5) return -9999;

  int commaCount = 0;
  int targetIndex = -1;

  for (int i = 1; i < len - 1; i++) {
    if (str[i] == ',') {
      if (commaCount == n) {
        targetIndex = i + 1;
        break;
      }
      commaCount++;
    }
  }

  if (targetIndex == -1) return -9999;
  return extractFloat(str, targetIndex);
}

float extractFloat(const char str[], int i) {
  if (str[i] == '\0') return -9999;

  char tempBuffer[20];
  int j = 0;

  while (str[i] != '\0' && j < 19) {
    if (isdigit(str[i]) || str[i] == '.' || str[i] == '-') {
      tempBuffer[j++] = str[i];
    } else if (j > 0) {
      break;
    }
    i++;
  }
  tempBuffer[j] = '\0';

  if (j == 0) return -9999;
  return atof(tempBuffer);
}

// ----------------------- Sequence Execution Functions -----------------------

void executeSequenceStep(const SequenceStep& step, float t_s) {
  uint8_t valve = step.valve;
  uint8_t action = step.action;

  // Execute the action just like manual commands
  if (action == 1) {  // Open valve
    if (valve >= 0 && valve <= 11) {
      startOpenValve(valve, t_s);
    } else if (valve >= 12) {
      char buffer[10];
      sprintf(buffer, "{%02d,01}", valve);
      Serial3.println(buffer);
      rs485ValveDesiredStates[valve - 12] = 1;
    }
  }
  else if (action == 2) {  // Close valve
    if (valve >= 0 && valve <= 11) {
      startCloseValve(valve, t_s);
    } else if (valve >= 12) {
      char buffer[10];
      sprintf(buffer, "{%02d,02}", valve);
      Serial3.println(buffer);
      rs485ValveDesiredStates[valve - 12] = 0;
    }
  }
  else if (action == 3) {  // Fire pyro
    if (valve == 0) {
      pyro1Start_s = t_s;
      pyro1 = 1;
    } else if (valve == 1) {
      pyro2Start_s = t_s;
      pyro2 = 1;
    }
  }
}

void updateSequence(float t_s) {
  if (sequenceState == SEQ_IDLE) {
    return;
  }

  // -------- BURN STATE --------
  if (sequenceState == SEQ_BURN) {
    float burnElapsed = t_s - burnWaitStartTime_s;
    
    // Check if burn duration has elapsed
    if (burnElapsed >= burnDuration_s) {
      // Burn complete, move to next step
      sequenceState = SEQ_SHUTDOWN;
      lastStepTime_s = t_s;
      currentStepIndex++;
      
      Serial.println("{5,BURN_COMPLETE}");
    }
    return;
  }
  
  // -------- STARTUP/SHUTDOWN STATE --------
  if (sequenceState == SEQ_STARTUP || sequenceState == SEQ_SHUTDOWN) {
    // Check if there are more steps
    if (currentStepIndex >= HOTFIRE_SEQ_LENGTH) {
      sequenceState = SEQ_IDLE;
      Serial.println("{5,SEQUENCE_COMPLETE}");
      return;
    }
    
    // Check if it's time to execute the current step
    float timeSinceLastStep = t_s - lastStepTime_s;
    
    if (timeSinceLastStep >= hotfireSequence[currentStepIndex].time_s) {
      const SequenceStep& step = hotfireSequence[currentStepIndex];
      
      // Check if this is a burn wait step
      if (step.action == 4) {
        // Enter burn state
        sequenceState = SEQ_BURN;
        burnWaitStartTime_s = t_s;
        
        Serial.print("{5,BURN_STARTED,");
        Serial.print(burnDuration_s);
        Serial.println("}");
      } else {
        // Execute the step
        executeSequenceStep(step, t_s);
        
        // Move to next step
        lastStepTime_s = t_s;
        currentStepIndex++;
      }
    }
  }
}

void printSequenceStatus() {
  // Send sequence telemetry: state, current step, and elapsed time
  Serial.print("{5,");
  Serial.print((int)sequenceState);
  Serial.print(",");
  Serial.print(currentStepIndex);
  Serial.print(",");
  
  if (sequenceState == SEQ_STARTUP || sequenceState == SEQ_SHUTDOWN) {
    float timeSinceLastStep = (millis() / 1000.0f) - lastStepTime_s;
    Serial.print(timeSinceLastStep);
  } else if (sequenceState == SEQ_BURN) {
    float burnElapsed = (millis() / 1000.0f) - burnWaitStartTime_s;
    Serial.print(burnElapsed);
  } else {
    Serial.print("0");
  }
  
  Serial.println("}");
}