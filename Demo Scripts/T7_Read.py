from datetime import datetime
import sys

from labjack import ljm

MAX_REQUESTS = 10  # The number of eStreamRead calls that will be performed.

handle = ljm.openS("T7", "USB", "ANY")  # Any device, Any connection, Any identifier

info = ljm.getHandleInfo(handle)
print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
      "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
      (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))

deviceType = info[0]

#Stream config
aScanListNames = ["AIN0", "AIN1"]  # Scan list names to stream
numAddresses = len(aScanListNames)
aScanList = ljm.namesToAddresses(numAddresses, aScanListNames)[0]
scanRate = 10000
scansPerRead = int(scanRate / numAddresses)


try:
    # When streaming, negative channels and ranges can be configured for
    # individual analog inputs, but the stream has only one settling time and
    # resolution.

    if deviceType == ljm.constants.dtT4:
        # LabJack T4 configuration

        # Stream settling is 0 (default) and
        # stream resolution index is 0 (default).
        aNames = ["STREAM_SETTLING_US", "STREAM_RESOLUTION_INDEX"]
        aValues = [0, 0]
    else:
        # LabJack T7 and T8 configuration

        # Ensure triggered stream is disabled.
        ljm.eWriteName(handle, "STREAM_TRIGGER_INDEX", 0)
        # Enabling internally-clocked stream.
        ljm.eWriteName(handle, "STREAM_CLOCK_SOURCE", 0)

        # AIN0 and AIN1 ranges are +/-10 V and stream resolution index is
        # 0 (default).
        aNames = ["AIN0_RANGE", "AIN1_RANGE", "STREAM_RESOLUTION_INDEX"]
        aValues = [10.0, 10.0, 0]

        # Negative channel and settling configurations do not apply to the T8
        if deviceType == ljm.constants.dtT7:
            #     Negative Channel = 199 (Single-ended)
            #     Settling = 0 (auto)
            aNames.extend(["AIN0_NEGATIVE_CH", "STREAM_SETTLING_US",
                           "AIN1_NEGATIVE_CH"])
            aValues.extend([199, 0, 199])

    # Write the analog inputs' negative channels (when applicable), ranges,
    # stream settling time and stream resolution configuration.
    numFrames = len(aNames)
    ljm.eWriteNames(handle, numFrames, aNames, aValues)

    # Configure and start stream
    scanRate = ljm.eStreamStart(handle, scansPerRead, numAddresses, aScanList, scanRate)
    print("\nStream started with a scan rate of %0.0f Hz." % scanRate)

    print("\nPerforming %i stream reads." % MAX_REQUESTS)
    start = datetime.now()
    totScans = 0
    totSkip = 0  # Total skipped samples

    i = 1
    while i <= MAX_REQUESTS:
        ret = ljm.eStreamRead(handle)

        aData = ret[0]
        scans = len(aData) / numAddresses
        totScans += scans

        # Count the skipped samples which are indicated by -9999 values. Missed
        # samples occur after a device's stream buffer overflows and are
        # reported after auto-recover mode ends.
        curSkip = aData.count(-9999.0)
        totSkip += curSkip

        #print("\neStreamRead %i" % i)
        #ainStr = ""
        #for j in range(0, numAddresses):
        #    ainStr += "%s = %0.5f, " % (aScanListNames[j], aData[j])
        #print("  1st scan out of %i: %s" % (scans, ainStr))
        #print("  Scans Skipped = %0.0f, Scan Backlogs: Device = %i, LJM = "
        #      "%i" % (curSkip/numAddresses, ret[1], ret[2]))
        #i += 1

        print(aScanListNames[0], aData[0])

    end = datetime.now()

    print("\nTotal scans = %i" % (totScans))
    tt = (end - start).seconds + float((end - start).microseconds) / 1000000
    print("Time taken = %f seconds" % (tt))
    print("LJM Scan Rate = %f scans/second" % (scanRate))
    print("Timed Scan Rate = %f scans/second" % (totScans / tt))
    print("Timed Sample Rate = %f samples/second" % (totScans * numAddresses / tt))
    print("Skipped scans = %0.0f" % (totSkip / numAddresses))
except ljm.LJMError:
    ljme = sys.exc_info()[1]
    print(ljme)
except Exception:
    e = sys.exc_info()[1]
    print(e)

try:
    print("\nStop Stream")
    ljm.eStreamStop(handle)
except ljm.LJMError:
    ljme = sys.exc_info()[1]
    print(ljme)
except Exception:
    e = sys.exc_info()[1]
    print(e)

# Close handle
ljm.close(handle)