#include <Servo.h>
#include <Wire.h>

#define LINK_SERIAL Serial1

void debugLog(const char* message) {
  Serial.println(message);
}

void debugLogCommand(const char* stage, int commandAddress, int commandInt) {
  Serial.print("[ECU] ");
  Serial.print(stage);
  Serial.print(" addr=");
  Serial.print(commandAddress);
  Serial.print(" cmd=");
  Serial.println(commandInt);
}

// uint8_t valveStates[12] = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 };
// uint8_t valvePins[12] = { 13, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 };
// bool valveIsCryo[12] = { true, true, true, true, true, true, true, true, true, true, true, false };
// float valveAngle[12] = {};
// bool valveClosing[12] = {};
// bool needsOpeningBackoff[12] = {};
// bool needsClosingBackoff[12] = {};
// float lastOpeningCommand[12] = {};
// float lastClosingCommand[12] = {};
// uint8_t limitSwitchPins[12] = {
//   27,
//   29,
//   31,
//   33,
//   35,
//   37,
//   39,
//   41,
//   43,
//   45,
//   47,
//   49,
// };

// RS485 valves  
uint8_t rs485ValveAddresses[24] = { 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35 };
uint8_t rs485ValveAngles[24] = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 };
uint8_t rs485ValveDesiredStates[24] = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 };

float lastValveStatePrint = 0.0;
float lastPTTCPrint = 0.125; // Start 1/8 sec out of phase to avoid blowing up loop
bool telemetryRequested = false;

// Incoming messagse serial que
char partialCommand[100] = "";
int partialCommandIndex = 0;

int nonCryo_open = 10;
int nonCryo_mostlyClosed = 75;
int nonCryo_closed = 130;
int nonCryo_closeBackoff = 8;
int nonCryo_openBackoff = 5;
float nonCryo_openBackoffDelay = 2;
float nonCryo_closeBackoffDelay = 0.5;

int cryo_open = 160;
int cryo_mostlyClosed = 50;
int cryo_closed = 10;
int cryo_closeBackoff = 2;
int cryo_openBackoff = 2;
float cryo_openBackoffDelay = 2.5;
float cryo_closeBackoffDelay = 0.5;


uint8_t pyro1 = 0;
uint8_t pyro2 = 0;

double pyro1Start = 0;
double pyro2Start = 0;

#define PYRO1_PIN 22
#define PYRO2_PIN 24

// TC Registers
#define REG_HOT_JUNCTION_TEMP 0x00  // Hot Junction Temperature Register
#define REG_COLD_JUNCTION_TEMP 0x02 // Cold Junction Temperature Register
#define REG_THERMOCOUPLE_CFG 0x05   // Thermocouple Configuration Register

// PT List, need to list Min, Max pressure, Min, Max Output, attatchment pins, names
float ptPressureRange[4][2] = {{0, 1000}, {0, 100}, {0, 100}, {0, 100}};
float ptOutputRange[4][2] = {{0.5, 4.5}, {0, 5}, {0, 5}, {0, 5}};
uint8_t ptPins[4] = {0, 1, 2, 3};
float ptValue[4] = {0.0, 0.0, 0.0, 0.0};
//char ptNames[4][12] = {"PT1", "PT2", "PT3", "PT4"};
uint8_t ptIds[4] = {0, 1, 2, 3};

// TC List, need to store TC Address, name, type
uint8_t tcAddress[4] = {0x61, 0x62, 0x63, 0x64};
float tcHotValue[4] = {0.0, 0.0, 0.0, 0.0};
float tcColdValue[4] = {0.0, 0.0, 0.0, 0.0};
uint8_t tcIds[4] = {4, 5, 6, 7};

// ECU-side sequence commands
#define ECU_CMD_STOP_SEQUENCE 21
#define ECU_CMD_UPLOAD_SEQUENCE_BEGIN 30
#define ECU_CMD_UPLOAD_SEQUENCE_STEP 31
#define ECU_CMD_UPLOAD_SEQUENCE_START 32

// ECU-side sequence actions
#define ECU_SEQUENCE_ACTION_OPEN 1
#define ECU_SEQUENCE_ACTION_CLOSE 2
#define ECU_SEQUENCE_ACTION_WAIT 3
#define ECU_SEQUENCE_ACTION_FIRE 4
#define ECU_SEQUENCE_ACTION_POLL 5

#define ECU_UPLOADED_SEQUENCE_MAX_STEPS 160

struct EcuSequenceStep {
  uint8_t action;
  uint8_t valveAddress;
  uint16_t waitMs;
};

bool ecuSequenceRunning = false;
int ecuSequenceStepIndex = 0;
unsigned long ecuSequenceNextStepAtMs = 0;

EcuSequenceStep ecuUploadedSequence[ECU_UPLOADED_SEQUENCE_MAX_STEPS];
int ecuUploadedSequenceExpectedSteps = 0;
int ecuUploadedSequenceCount = 0;
bool ecuSequenceUploadInProgress = false;

bool forwardRs485ValveCommand(int commandAddress, int valveCommand) {
  if (commandAddress < 12 || commandAddress > 35) {
    return false;
  }

  char buffer[10];
  sprintf(buffer, "{%02d,%02d}", commandAddress, valveCommand);

  if (valveCommand == 1) {
    Serial.print("[ECU] forwarding open to RS485: ");
  } else {
    Serial.print("[ECU] forwarding close to RS485: ");
  }
  Serial.println(buffer);

  Serial3.println(buffer);
  rs485ValveDesiredStates[commandAddress - 12] = (valveCommand == 1) ? 1 : 0;
  return true;
}

bool startUploadedSequence() {
  if (ecuUploadedSequenceCount <= 0) {
    Serial.println("[ECU] uploaded sequence empty");
    return false;
  }

  ecuSequenceRunning = true;
  ecuSequenceStepIndex = 0;
  ecuSequenceNextStepAtMs = millis();

  Serial.print("[ECU] uploaded sequence started steps=");
  Serial.println(ecuUploadedSequenceCount);
  return true;
}

bool beginUploadedSequence(int expectedSteps) {
  if (expectedSteps <= 0 || expectedSteps > ECU_UPLOADED_SEQUENCE_MAX_STEPS) {
    Serial.print("[ECU] invalid upload step count: ");
    Serial.println(expectedSteps);
    return false;
  }

  ecuSequenceUploadInProgress = true;
  ecuUploadedSequenceExpectedSteps = expectedSteps;
  ecuUploadedSequenceCount = 0;
  stopEcuSequence();

  Serial.print("[ECU] upload begin expected steps=");
  Serial.println(expectedSteps);
  return true;
}

bool addUploadedSequenceStep(int stepIndex, uint8_t action, uint8_t target, uint16_t value) {
  if (!ecuSequenceUploadInProgress) {
    Serial.println("[ECU] upload step rejected (no upload in progress)");
    return false;
  }

  if (stepIndex < 0 || stepIndex >= ecuUploadedSequenceExpectedSteps || stepIndex >= ECU_UPLOADED_SEQUENCE_MAX_STEPS) {
    Serial.print("[ECU] upload step rejected (bad index) index=");
    Serial.println(stepIndex);
    return false;
  }

  if (stepIndex < ecuUploadedSequenceCount) {
    const EcuSequenceStep& existingStep = ecuUploadedSequence[stepIndex];
    if (existingStep.action == action && existingStep.valveAddress == target && existingStep.waitMs == value) {
      Serial.print("[ECU] upload step duplicate ack index=");
      Serial.println(stepIndex);
      return true;
    }

    Serial.print("[ECU] upload step rejected (conflicting retry) index=");
    Serial.println(stepIndex);
    return false;
  }

  if (stepIndex > ecuUploadedSequenceCount) {
    Serial.print("[ECU] upload step rejected (out of order) index=");
    Serial.print(stepIndex);
    Serial.print(" expected=");
    Serial.println(ecuUploadedSequenceCount);
    return false;
  }

  if (ecuUploadedSequenceCount >= ecuUploadedSequenceExpectedSteps || ecuUploadedSequenceCount >= ECU_UPLOADED_SEQUENCE_MAX_STEPS) {
    Serial.println("[ECU] upload step rejected (buffer full)");
    return false;
  }

  ecuUploadedSequence[stepIndex].action = action;
  ecuUploadedSequence[stepIndex].valveAddress = target;
  ecuUploadedSequence[stepIndex].waitMs = value;
  ecuUploadedSequenceCount += 1;
  return true;
}

bool finalizeUploadedSequence() {
  if (!ecuSequenceUploadInProgress) {
    Serial.println("[ECU] upload finalize rejected (no upload in progress)");
    return false;
  }

  ecuSequenceUploadInProgress = false;
  if (ecuUploadedSequenceCount != ecuUploadedSequenceExpectedSteps) {
    Serial.print("[ECU] upload finalize count mismatch count=");
    Serial.print(ecuUploadedSequenceCount);
    Serial.print(" expected=");
    Serial.println(ecuUploadedSequenceExpectedSteps);
    return false;
  }

  return true;
}

void stopEcuSequence() {
  if (ecuSequenceRunning) {
    Serial.println("[ECU] sequence stopped");
  }

  ecuSequenceRunning = false;
  ecuSequenceStepIndex = 0;
  ecuSequenceNextStepAtMs = 0;
}

void updateEcuSequence() {
  if (!ecuSequenceRunning) {
    return;
  }

  unsigned long nowMs = millis();
  if ((long)(nowMs - ecuSequenceNextStepAtMs) < 0) {
    return;
  }

  if (ecuSequenceStepIndex >= ecuUploadedSequenceCount) {
    Serial.print("[ECU] sequence complete: executed ");
    Serial.print(ecuSequenceStepIndex);
    Serial.print(" of ");
    Serial.println(ecuUploadedSequenceCount);
    stopEcuSequence();
    return;
  }

  const EcuSequenceStep& step = ecuUploadedSequence[ecuSequenceStepIndex];
  
  Serial.print("[ECU SEQ] step ");
  Serial.print(ecuSequenceStepIndex);
  Serial.print(" action=");
  Serial.print(step.action);
  Serial.print(" target=");
  Serial.print(step.valveAddress);
  Serial.print(" value=");
  Serial.println(step.waitMs);

  if (step.action == ECU_SEQUENCE_ACTION_OPEN) {
    Serial.print("[ECU SEQ] OPEN valve addr=");
    Serial.println(step.valveAddress);
    forwardRs485ValveCommand(step.valveAddress, 1);
    ecuSequenceNextStepAtMs = nowMs;
  } else if (step.action == ECU_SEQUENCE_ACTION_CLOSE) {
    Serial.print("[ECU SEQ] CLOSE valve addr=");
    Serial.println(step.valveAddress);
    forwardRs485ValveCommand(step.valveAddress, 2);
    ecuSequenceNextStepAtMs = nowMs;
  } else if (step.action == ECU_SEQUENCE_ACTION_WAIT) {
    Serial.print("[ECU SEQ] WAIT for ");
    Serial.print(step.waitMs);
    Serial.println("ms");
    ecuSequenceNextStepAtMs = nowMs + step.waitMs;
  } else if (step.action == ECU_SEQUENCE_ACTION_FIRE) {
    int pyroIndex = step.valveAddress;
    Serial.print("[ECU SEQ] FIRE pyro index=");
    Serial.println(pyroIndex);
    if (pyroIndex == 0) {
      pyro1Start = nowMs / 1000.0;
      pyro1 = 1;
    } else if (pyroIndex == 1) {
      pyro2Start = nowMs / 1000.0;
      pyro2 = 1;
    }
    ecuSequenceNextStepAtMs = nowMs;
  } else if (step.action == ECU_SEQUENCE_ACTION_POLL) {
    Serial.println("[ECU SEQ] POLL");
    updateRS485ValveAngles();
    telemetryRequested = true;
    ecuSequenceNextStepAtMs = nowMs;
  } else {
    Serial.print("[ECU SEQ] UNKNOWN action ");
    Serial.println(step.action);
    ecuSequenceNextStepAtMs = nowMs;
  }

  ecuSequenceStepIndex += 1;
}

void sendAck(int commandAddress, int commandInt) {
  debugLogCommand("sending ack", commandAddress, commandInt);
  LINK_SERIAL.print("{7,");
  LINK_SERIAL.print(commandAddress);
  LINK_SERIAL.print(",");
  LINK_SERIAL.print(commandInt);
  LINK_SERIAL.println("}");
}

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  LINK_SERIAL.begin(9600);
  Serial3.begin(115200);
  Serial3.setTimeout(10);
  Wire.begin();
  Wire.setWireTimeout(3000, true); // 3ms I2C timeout, reset bus on lockup

  debugLog("[ECU] setup complete");

  pinMode(A4, INPUT);

  // for (int i = 0; i < 12; i++) {
  //   pinMode(valvePins[i], OUTPUT);
  //   pinMode(limitSwitchPins[i], INPUT);

  //   valveAngle[i] = valveIsCryo[i] ? cryo_mostlyClosed : nonCryo_mostlyClosed;
  // }

  pinMode(46, OUTPUT);

  // Pyro setup
  pinMode(PYRO1_PIN, OUTPUT);
  pinMode(PYRO2_PIN, OUTPUT);
  digitalWrite(PYRO1_PIN, LOW);
  digitalWrite(PYRO2_PIN, LOW);

  // Configureing pinmodes for the PT sensors
  for (int i = 0; i < (sizeof(ptPins) / sizeof(ptPins[0])); i++)
  {
    pinMode(ptPins[i], INPUT);
  }

  // Config for the TCs
  for (int i = 0; i < (sizeof(tcAddress) / sizeof(tcAddress[0])); i++)
  {
    configureSensor(tcAddress[i]);
  }
}



void loop() {
  float t = millis() / 1000.0;

  // Read for input commands
  //  '{' => start command
  //  '}' => end command
  // Command structure will be{AA,XX,D...D(optional)}
  // AA will be address of valve or pyro channel, AA = 0 for general ECU command
  // XX will be the command int so 1 for open valve, 2 for close valve, 3 for fire pyro, 4 for relay to RS485 everything in the DDDD block, essentially strip the AA,XX fields
  char command[100] = "";
  int commandInt = 0;
  int commandAddress = 0;
  int commandEndIndex = 0;

  while (LINK_SERIAL.available()) {
    char nextChar = char(LINK_SERIAL.read());
    if (nextChar == '{') {
      partialCommand[0] = '{';
      partialCommandIndex = 1;
    } else if (nextChar == '}') {
      commandEndIndex = partialCommandIndex;
      partialCommand[partialCommandIndex] = '}';

      for (int i = 0;
           // Allows changing the size of the partialCommand buffer
           i < (sizeof(partialCommand) / sizeof(partialCommand[0]));
           i++) {
        if (i <= partialCommandIndex) {
          command[i] = partialCommand[i];
        } else {
          command[i] = '_';
        }
      }

      commandInt = extractIntAfterNthComma(command, 0);
      commandAddress = extractIntAfterNthComma(command, -1);
      Serial.print("[ECU] raw command: ");
      Serial.println(command);
      debugLogCommand("parsed", commandAddress, commandInt);
      // lastRecieveTime = t;
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

  if (commandInt == 1) {
    if (forwardRs485ValveCommand(commandAddress, 1)) {
      sendAck(commandAddress, commandInt);
    }
  }

  if (commandInt == 2) {
    if (forwardRs485ValveCommand(commandAddress, 2)) {
      sendAck(commandAddress, commandInt);
    }
  }

  if (commandInt == 3) {
    int pyroIndex = commandAddress;
    if (pyroIndex == 0) {
      pyro1Start = t;
      pyro1 = 1;
    }

    else if (pyroIndex == 1) {
      pyro2Start = t;
      pyro2 = 1;
    }

    Serial.print("[ECU] pyro command accepted index=");
    Serial.println(pyroIndex);
    sendAck(commandAddress, commandInt);
  }

  if (commandInt == 4) {
    int indexOfSecondComma = indexOfNthComma(command, 1);

    Serial3.print("{");  // prefix
    for (int i = indexOfSecondComma + 1; i <= commandEndIndex && command[i] != '\0'; i++) {
      Serial3.print(command[i]);
    }
    Serial3.println();
  }

  if (commandInt == 5) {
    debugLog("[ECU] telemetry poll received");
    updateRS485ValveAngles();
    telemetryRequested = true;
  }

  if (commandInt == ECU_CMD_STOP_SEQUENCE) {
    stopEcuSequence();
    sendAck(commandAddress, commandInt);
  }

  if (commandInt == ECU_CMD_UPLOAD_SEQUENCE_BEGIN) {
    int expectedSteps = extractIntAfterNthComma(command, 1);
    if (beginUploadedSequence(expectedSteps)) {
      sendAck(commandAddress, commandInt);
    }
  }

  if (commandInt == ECU_CMD_UPLOAD_SEQUENCE_STEP) {
    int stepIndex = extractIntAfterNthComma(command, 1);
    int action = extractIntAfterNthComma(command, 2);
    int target = extractIntAfterNthComma(command, 3);
    int value = extractIntAfterNthComma(command, 4);

    if (stepIndex >= 0 && action >= 0 && target >= 0 && value >= 0) {
      if (addUploadedSequenceStep(stepIndex, (uint8_t)action, (uint8_t)target, (uint16_t)value)) {
        sendAck(commandAddress, commandInt);
      }
    }
  }

  if (commandInt == ECU_CMD_UPLOAD_SEQUENCE_START) {
    if (finalizeUploadedSequence() && startUploadedSequence()) {
      sendAck(commandAddress, commandInt);
    }
  }

  updateEcuSequence();

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

  // Handling valve updates and backoffs
  // Open backoff delays
  // for (int i = 0; i < (sizeof(servos) / sizeof(servos[0])); i++) {
  //   if (needsOpeningBackoff[i] && (t - lastOpeningCommand[i]) > (valveIsCryo[i] ? cryo_openBackoffDelay : nonCryo_openBackoffDelay)) {
  //     needsOpeningBackoff[i] = false;
  //     if (valveIsCryo[i]) {
  //       servos[i].write(cryo_open);
  //       valveAngle[i] = cryo_open;
  //     } else {
  //       servos[i].write(nonCryo_open);
  //       valveAngle[i] = nonCryo_open;
  //     }
  //   }

  //   if (needsClosingBackoff[i] && (t - lastClosingCommand[i]) > (valveIsCryo[i] ? cryo_closeBackoffDelay : nonCryo_closeBackoffDelay)) {
  //     needsClosingBackoff[i] = false;
  //     if (valveIsCryo[i]) {
  //       servos[i].write(valveAngle[i] + cryo_closeBackoff);
  //       valveAngle[i] = valveAngle[i] + cryo_closeBackoff;
  //     } else {
  //       servos[i].write(valveAngle[i] - nonCryo_closeBackoff);
  //       valveAngle[i] = valveAngle[i] - nonCryo_closeBackoff;
  //     }
  //   }

  //   if (valveClosing[i]) {
  //     if ((digitalRead(limitSwitchPins[i]) == 1) || (valveIsCryo[i] ? (valveAngle[i] < cryo_closed) : (valveAngle[i] > nonCryo_closed))) {
  //       valveClosing[i] = 0;

  //       needsClosingBackoff[i] = true;
  //       lastClosingCommand[i] = t;

  //       // servos[i].write(valveAngle[i] - 1.5);
  //       // valveAngle[i] = valveAngle[i] - 1.5;

  //       // servos[i].write(valveAngle[i] - backoff);
  //       // valveAngle[i] = valveAngle[i] - backoff;
  //     } else if ((t - lastClosingCommand[i]) > 0.5) {
  //       if (valveIsCryo[i]) {
  //         servos[i].write(valveAngle[i] - 0.5);
  //         valveAngle[i] = valveAngle[i] - 0.5;
  //       } else {
  //         servos[i].write(valveAngle[i] + 0.5);
  //         valveAngle[i] = valveAngle[i] + 0.5;
  //       }
  //     }
  //   }
  // }

  delay(20);

  // Battery sensor
  float batteryVoltage = analogRead(4) / 1023.0 * 5.0 * 2.0;

  // Serial.println("{1,0,1,1,2,3,4}");
  // Serial.println("Line");
  if (telemetryRequested) {
    debugLog("[ECU] sending telemetry block");
    printDesiredValveStates();
    printActualValveStates();
    LINK_SERIAL.print("{3,");
    LINK_SERIAL.print(batteryVoltage);
    LINK_SERIAL.println("}");
    printRS485ValvePercentages();
    lastValveStatePrint = t;

    // Read sensors only when the app asks for telemetry.
    for (int i = 0; i < (sizeof(ptPins) / sizeof(ptPins[0])); i++)
    {
      ptValue[i] = (analogRead(ptPins[i]) / 1023.0 * 5.0 - ptOutputRange[i][0]) / (ptOutputRange[i][1] - ptOutputRange[i][0]) * (ptPressureRange[i][1] - ptPressureRange[i][0]) + ptPressureRange[i][0];
    }

    for (int i = 0; i < (sizeof(tcAddress) / sizeof(tcAddress[0])); i++)
    {
      tcHotValue[i] = readTempRegister(tcAddress[i], REG_HOT_JUNCTION_TEMP);
      tcColdValue[i] = readTempRegister(tcAddress[i], REG_COLD_JUNCTION_TEMP);
    }

    lastPTTCPrint = t;
    printPTReadings();
    printTCReadings();
    telemetryRequested = false;
    debugLog("[ECU] telemetry block complete");
  }

  digitalWrite(46, (rs485ValveAngles[0] <= 30 || rs485ValveAngles[0] > 80) ? 1 : 0);
}



// void moveServoUntilLimit() {
//   for (int pos = open; pos <= 120; pos += 1) {
//     if (digitalRead(45) == HIGH) {
//       Serial.println("Limit switch hit!");
//       delay(500);
//       servo1.write(pos-10);
//       break;
//     }
//     servo1.write(pos);
//     delay(15);
//   }
// }

void updateRS485ValveAngles() {
  char buf[40];
  char cmd[16];

  for (int i = 0; i < 24; i++) {
    int addr = rs485ValveAddresses[i];
    sprintf(cmd, "{%02d,32}", addr);

    // Flush leftover bytes
    while (Serial3.available()) Serial3.read();

    // Send query
    Serial3.print(cmd);
    Serial3.flush();

    // Give valve a short turnaround window
    // delay(2); // ~8ms — good balance for fast slaves

    // Wait briefly for start of reply
    unsigned long start = millis();
    while (!Serial3.available() && (millis() - start) < 3) {
      delayMicroseconds(200);
    }


    int len = Serial3.readBytesUntil('}', buf, sizeof(buf) - 1);
    buf[len] = '}';
    buf[len + 1] = '\0';
    // Serial.println("B");
    // Serial.println(buf);

    int v = -1, angle = -1;
    if (sscanf(buf, "{v,%d,%d}", &v, &angle) == 2) {
      rs485ValveAngles[v - 12] = angle;
      // Serial.print("Got valve ");
      // Serial.print(v);
      // Serial.print(" angle ");
      // Serial.println(angle);
    }
    // } else {
    //   Serial.print("No valid response from valve ");
    //   Serial.println(addr);
    //   Serial.print("Raw: ");
    //   Serial.println(buf);
    // }

    // Minimal gap before next valve
    delay(2);
  }
}


// void updateRS485ValveAngles() {
//   int value = 7;
//   char buf[10];


//   for(int i = 0; i < 12; i ++){
//     // Send command out for request for data
//     Serial3.print("{");

//     sprintf(buf, "%02d", rs485ValveAddresses[i]);
//     Serial3.print(buf);

//     Serial3.println(",32}");

//     delay(20); // give time to respond, command out should take <1ms, command back print time should be <1ms, 3ms for valve to "think"

//     // Read response
//     if (Serial3.available()) {
//       char buf[20];
//       Serial3.readBytesUntil('}', buf, sizeof(buf)-1);
//       buf[strcspn(buf, "\r\n")] = '\0'; // strip newline if any

//       Serial.println(buf);

//       int AA, DDD;
//       if (sscanf(buf, "{v%d,%d", &AA, &DDD) == 2) {
//         Serial.print("AA="); Serial.print(AA);

//         rs485ValveAngles[AA-12] = DDD;

//         Serial.print(" DDD="); Serial.println(rs485ValveAngles[AA-12]);
//       }
//     } else {
//       // Not connected
//       // Don't do anything

//     }

//     // Little extra delay
//     delay(10);

//   }
// }

void printDesiredValveStates() {
  LINK_SERIAL.print("{1");
  for (int i = 0; i < 12; i++) {
    LINK_SERIAL.print(",");
    LINK_SERIAL.print(rs485ValveDesiredStates[i]);
  }
  LINK_SERIAL.println("}");
}

void printActualValveStates() {
  LINK_SERIAL.print("{2");
  for (int i = 0; i < 24; i++) {
    LINK_SERIAL.print(",");
    uint8_t angle = rs485ValveAngles[i];
    if (angle > 30 && angle < 80) {
      LINK_SERIAL.print("0");  // Closed
    } else {
      LINK_SERIAL.print("1");  // Open
    }
  }
  LINK_SERIAL.println("}");
}


void printRS485ValvePercentages() {
  LINK_SERIAL.print("{4");
  for (int i = 0; i < 24; i++) {
    LINK_SERIAL.print(",");
    uint8_t angle = rs485ValveAngles[i]; //raw angle received
    int percent = angle - 50;   // convert raw angle to percent 
    LINK_SERIAL.print(percent);      //Removed constrain to see if any weird values occur
  }

  LINK_SERIAL.println("}");
}

void printPTReadings() {
  LINK_SERIAL.print("{5");
  // Support adding more PTs without changing code
  for (int i = 0; i < sizeof(ptPins)/sizeof(ptPins[0]); i++) {
    LINK_SERIAL.print(",");
    LINK_SERIAL.print(ptValue[i]);
  }
  LINK_SERIAL.println("}");
}

void printTCReadings() {
  LINK_SERIAL.print("{6");
  // Support adding more PTs without changing code
  for (int i = 0; i < sizeof(tcAddress)/sizeof(tcAddress); i++) {
    LINK_SERIAL.print(",");
    LINK_SERIAL.print(tcHotValue[i]);
    LINK_SERIAL.print(",");
    LINK_SERIAL.print(tcColdValue[i]);
  }
  LINK_SERIAL.println("}");
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

  if (n == -1) {
    return extractInt(str, 1);
  }

  int targetIndex = indexOfNthComma(str, n) + 1;  // The number starts after this comma

  if (targetIndex == -1) return -9999;  // nth comma not found

  // Extract integer after the nth comma using extractInt function
  return extractInt(str, targetIndex);
}

int indexOfNthComma(const char str[], int n) {
  int commaCount = 0;
  int targetIndex = -1;

  // Find the nth comma
  for (int i = 1; i < strlen(str) - 1; i++) {  // Ignore first '{' and last '}'
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

// Write registers from TC chips
void writeRegister(uint8_t addr, uint8_t reg, uint8_t value)
{
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(value);
  Wire.endTransmission();
}

// Configure thermocouple wtih type
void configureSensor(uint8_t addr)
{
  // 0 is type K, only type being used
  writeRegister(addr, REG_THERMOCOUPLE_CFG, 0);
  // Serial.print("Set sensor at 0x");
  // Serial.print(addr, HEX);
  // Serial.print(" to Type: ");
  // Serial.println(type);
}

// Read registers from TC chips
float readTempRegister(uint8_t addr, uint8_t reg)
{
  Wire.beginTransmission(addr);
  Wire.write(reg);
  byte err = Wire.endTransmission();
  if (err != 0) return NAN; // No device at address

  Wire.requestFrom(addr, (uint8_t)2);
  if (Wire.getWireTimeoutFlag()) {
    Wire.clearWireTimeoutFlag();
    return NAN; // I2C bus locked up
  }
  if (Wire.available() < 2)
  {
    return NAN; // Return NaN if no response
  }

  int16_t rawData = (Wire.read() << 8) | Wire.read();

  return rawData * 0.0625; // Convert raw data to temperature in °C
}
