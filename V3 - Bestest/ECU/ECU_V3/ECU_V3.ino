#include <Servo.h>

uint8_t valveStates[14] = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 };
uint8_t valvePins[12] = { 13, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 };
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

float lastValveStatePrint = 0.0;

// Incoming messagse serial que
char partialCommand[100] = "";
int partialCommandIndex = 0;

Servo servos[12];

int open = 40;
int mostlyClosed = 100;
int closed = 140;
int closeBackoff = 4;
int openBackoff = 5;
float openBackoffDelay = 2;
float closeBackoffDelay = 0.5;

bool movingToClose = false;

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);

  pinMode(A4, INPUT);

  for (int i = 0; i < 12; i++) {
    pinMode(valvePins[i], OUTPUT);
    pinMode(limitSwitchPins[i], INPUT);

    servos[i].attach(valvePins[i]);

    valveAngle[i] = mostlyClosed;
  }

  for (int i = 0; i < 14; i++) {
    servos[i].write(mostlyClosed);
  }

  pinMode(46, OUTPUT);
}



void loop() {
  float t = millis() / 1000.0;

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
    int valveIndex = extractIntAfterNthComma(command, 0);

    if (valveIndex >= 0 && valveIndex <= 11) {  // Checking that the index is within range
      if (valveStates[valveIndex] == 0) {
        valveStates[valveIndex] = 1;
        valveAngle[valveIndex] = open - openBackoff;
        servos[valveIndex].write(open - openBackoff);

        valveClosing[valveIndex] = false;
        needsClosingBackoff[valveIndex] = false;
        needsOpeningBackoff[valveIndex] = true;
        lastOpeningCommand[valveIndex] = t;
      }
    }
  }

  if (commandInt == 2) {
    int valveIndex = extractIntAfterNthComma(command, 0);

    if (valveIndex >= 0 && valveIndex <= 11) {
      if (valveStates[valveIndex] == 1) {  // Checking that the index is within range
        valveStates[valveIndex] = 0;
        servos[valveIndex].write(mostlyClosed);
        valveAngle[valveIndex] = mostlyClosed;
        // servos[valveIndex].write(closed);

        valveClosing[valveIndex] = true;
        needsOpeningBackoff[valveIndex] = false;
        lastClosingCommand[valveIndex] = t;
      }
    }
  }

  // Handling valve updates and backoffs
  // Open backoff delays
  for (int i = 0; i < (sizeof(servos) / sizeof(servos[0])); i++) {
    if (needsOpeningBackoff[i] && (t - lastOpeningCommand[i]) > openBackoffDelay) {
      needsOpeningBackoff[i] = false;
      servos[i].write(open);
      valveAngle[i] = open;
    }

    if (needsClosingBackoff[i] && (t - lastClosingCommand[i]) > closeBackoffDelay) {
      needsClosingBackoff[i] = false;
      servos[i].write(valveAngle[i] - closeBackoff);
      valveAngle[i] = valveAngle[i] - closeBackoff;
    }

    if (valveClosing[i]) {
      if ((digitalRead(limitSwitchPins[i]) == 1) || valveAngle[i] > closed) {
        valveClosing[i] = 0;

        needsClosingBackoff[i] = true;
        lastClosingCommand[i] = t;

        servos[i].write(valveAngle[i] + 1.5);
        valveAngle[i] = valveAngle[i] + 1.5;

        // servos[i].write(valveAngle[i] - backoff);
        // valveAngle[i] = valveAngle[i] - backoff;
      } else if ((t - lastClosingCommand[i]) > 0.5) {
        servos[i].write(valveAngle[i] + 0.5);
        valveAngle[i] = valveAngle[i] + 0.5;
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
    printLimitSwitchValveStates();
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

void printDesiredValveStates() {
  Serial.print("{1");
  for (int i = 0; i < 14; i++) {
    Serial.print(",");
    Serial.print(valveStates[i]);
  }
  Serial.println("}");
}

void printLimitSwitchValveStates() {
  Serial.print("{2");
  for (int i = 0; i < 14; i++) {
    Serial.print(",");
    Serial.print(!digitalRead(limitSwitchPins[i]));
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