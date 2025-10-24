#include <Servo.h>
#include <MemoryFree.h>

uint8_t valveStates[12] = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 };
uint8_t valvePins[12] = { 13, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 };
bool valveIsCryo[12] = { true, false, false, false, false, false, false, false, false, false, false, false };
float valveAngle[12] = {};
bool valveClosing[12] = {};
bool needsOpeningBackoff[12] = {};
bool needsClosingBackoff[12] = {};
float lastOpeningCommand[12] = {};
float lastClosingCommand[12] = {};
uint8_t limitSwitchPins[12] = {
  27,
  29,
  31,
  33,
  35,
  37,
  39,
  41,
  43,
  45,
  47,
  49,
};

// RS485 valves
uint8_t rs485ValveAddresses[12] = { 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23 };
uint8_t rs485ValveAngles[12] = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 };
uint8_t rs485ValveDesiredStates[12] = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 };

float lastValveStatePrint = 0.0;

// Incoming messagse serial que
char partialCommand[100] = "";
int partialCommandIndex = 0;

Servo servos[12];

int nonCryo_open = 10;
int nonCryo_mostlyClosed = 75;
int nonCryo_closed = 130;
int nonCryo_closeBackoff = 8;
int nonCryo_openBackoff = 5;
float nonCryo_openBackoffDelay = 2;
float nonCryo_closeBackoffDelay = 0.5;

int cryo_open = 160;
int cryo_mostlyClosed = 30;
int cryo_closed = 10;
int cryo_closeBackoff = 2;
int cryo_openBackoff = 2;
float cryo_openBackoffDelay = 2;
float cryo_closeBackoffDelay = 0.5;


uint8_t pyro1 = 0;
uint8_t pyro2 = 0;

double pyro1Start = 0;
double pyro2Start = 0;

#define PYRO1_PIN 22
#define PYRO2_PIN 24

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  Serial3.begin(115200);
  Serial3.setTimeout(10);

  pinMode(A4, INPUT);

  for (int i = 0; i < 12; i++) {
    pinMode(valvePins[i], OUTPUT);
    pinMode(limitSwitchPins[i], INPUT);

    servos[i].attach(valvePins[i]);
    servos[i].write(valveIsCryo[i] ? cryo_mostlyClosed : nonCryo_mostlyClosed);

    valveAngle[i] = valveIsCryo[i] ? cryo_mostlyClosed : nonCryo_mostlyClosed;
  }

  pinMode(46, OUTPUT);

  // Pyro setup
  pinMode(PYRO1_PIN, OUTPUT);
  pinMode(PYRO2_PIN, OUTPUT);
  digitalWrite(PYRO1_PIN, LOW);
  digitalWrite(PYRO2_PIN, LOW);
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

  while (Serial.available()) {
    char nextChar = char(Serial.read());
    if (nextChar == '{') {
      partialCommand[0] = '{';
      partialCommandIndex = 1;
    } else if (nextChar == '}') {
      commandEndIndex = partialCommandIndex;
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

      commandInt = extractIntAfterNthComma(command, 0);
      commandAddress = extractIntAfterNthComma(command, -1);
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
    int valveIndex = commandAddress;

    // Servo valve
    if (valveIndex >= 0 && valveIndex <= 11) {  // Checking that the index is within range
      if (valveStates[valveIndex] == 0) {
        valveStates[valveIndex] = 1;

        if (valveIsCryo[valveIndex]) {
          valveAngle[valveIndex] = cryo_open + cryo_openBackoff;
          servos[valveIndex].write(cryo_open + cryo_openBackoff);
        } else {
          valveAngle[valveIndex] = nonCryo_open - nonCryo_openBackoff;
          servos[valveIndex].write(nonCryo_open - nonCryo_openBackoff);
        }

        valveClosing[valveIndex] = false;
        needsClosingBackoff[valveIndex] = false;
        needsOpeningBackoff[valveIndex] = true;
        lastOpeningCommand[valveIndex] = t;
      }
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

  if (commandInt == 2) {
    int valveIndex = commandAddress;

    // Servo motor valve
    if (valveIndex >= 0 && valveIndex <= 11) {
      if (valveStates[valveIndex] == 1) {  // Checking that the index is within range
        valveStates[valveIndex] = 0;

        if (valveIsCryo[valveIndex]) {
          servos[valveIndex].write(cryo_mostlyClosed);
          valveAngle[valveIndex] = cryo_mostlyClosed;
        } else {
          servos[valveIndex].write(nonCryo_mostlyClosed);
          valveAngle[valveIndex] = nonCryo_mostlyClosed;
        }

        valveClosing[valveIndex] = true;
        needsOpeningBackoff[valveIndex] = false;
        lastClosingCommand[valveIndex] = t;
      }
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
    updateRS485ValveAngles();
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

  // Handling valve updates and backoffs
  // Open backoff delays
  for (int i = 0; i < (sizeof(servos) / sizeof(servos[0])); i++) {
    if (needsOpeningBackoff[i] && (t - lastOpeningCommand[i]) > (valveIsCryo[i] ? cryo_openBackoffDelay : nonCryo_openBackoffDelay)) {
      needsOpeningBackoff[i] = false;
      if (valveIsCryo[i]) {
        servos[i].write(cryo_open);
        valveAngle[i] = cryo_open;
      } else {
        servos[i].write(nonCryo_open);
        valveAngle[i] = nonCryo_open;
      }
    }

    if (needsClosingBackoff[i] && (t - lastClosingCommand[i]) > (valveIsCryo[i] ? cryo_closeBackoffDelay : nonCryo_closeBackoffDelay)) {
      needsClosingBackoff[i] = false;
      if (valveIsCryo[i]) {
        servos[i].write(valveAngle[i] + cryo_closeBackoff);
        valveAngle[i] = valveAngle[i] + cryo_closeBackoff;
      } else {
        servos[i].write(valveAngle[i] - nonCryo_closeBackoff);
        valveAngle[i] = valveAngle[i] - nonCryo_closeBackoff;
      }
    }

    if (valveClosing[i]) {
      if ((digitalRead(limitSwitchPins[i]) == 1) || (valveIsCryo[i] ? (valveAngle[i] < cryo_closed) : (valveAngle[i] > nonCryo_closed))) {
        valveClosing[i] = 0;

        needsClosingBackoff[i] = true;
        lastClosingCommand[i] = t;

        // servos[i].write(valveAngle[i] - 1.5);
        // valveAngle[i] = valveAngle[i] - 1.5;

        // servos[i].write(valveAngle[i] - backoff);
        // valveAngle[i] = valveAngle[i] - backoff;
      } else if ((t - lastClosingCommand[i]) > 0.5) {
        if (valveIsCryo[i]) {
          servos[i].write(valveAngle[i] - 0.5);
          valveAngle[i] = valveAngle[i] - 0.5;
        } else {
          servos[i].write(valveAngle[i] + 0.5);
          valveAngle[i] = valveAngle[i] + 0.5;
        }
      }
    }
  }

  delay(20);

  // Battery sensor
  float batteryVoltage = analogRead(4) / 1023.0 * 5.0 * 2.0;

  // Serial.println("{1,0,1,1,2,3,4}");
  // Serial.println("Line");
  if ((t - lastValveStatePrint) > 0.25) {
    printDesiredValveStates();
    printActualValveStates();
    Serial.print("{3,");
    Serial.print(batteryVoltage);
    Serial.println("}");

    lastValveStatePrint = t;
  }

  digitalWrite(46, valveStates[0]);
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

  for (int i = 0; i < 12; i++) {
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
  Serial.print("{1");
  for (int i = 0; i < 12; i++) {
    Serial.print(",");
    Serial.print(valveStates[i]);
  }

  for (int i = 0; i < 12; i++) {
    Serial.print(",");
    Serial.print(rs485ValveDesiredStates[i]);
  }

  Serial.println("}");
}

void printActualValveStates() {
  Serial.print("{2");
  for (int i = 0; i < 12; i++) {
    Serial.print(",");
    Serial.print(!digitalRead(limitSwitchPins[i]));
  }

  for (int i = 0; i < 12; i++) {
    Serial.print(",");
    uint8_t angle = rs485ValveAngles[i];
    if (angle > 30 && angle < 80) {
      Serial.print("0");  // Closed
    } else {
      Serial.print("1");  // Open
    }
  }

  Serial.println("}");
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