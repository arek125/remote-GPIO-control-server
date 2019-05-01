/*
Usage: ./codesend decimalcode bcm_pin [protocol] [pulselength] [repeattransmit] [bitlength]
decimalcode     - As decoded by RFSniffer
bcm_pin         - BCM GPIO PIN of connected transmiter
protocol        - According to rc-switch definitions
pulselength     - pulselength in microseconds
repeattransmit  - number of transmit repeat

 'codesend' hacked from 'send' by @justy
 
 - The provided rc_switch 'send' command uses the form systemCode, unitCode, command
   which is not suitable for our purposes.  Instead, we call 
   send(code, length); // where length is always 24 and code is simply the code
   we find using the RF_sniffer.ino Arduino sketch.

*/
#include "../rc-switch/RCSwitch.h"
#include <stdlib.h>
#include <stdio.h>
     

int main(int argc, char *argv[]) {

    int protocol = 1; // A value of 0 will use rc-switch's default value
    int pulseLength = 0;
    int repeatTransmit = 10;
    int bitlength = 24;

    // If no command line argument is given, print the help text
    if (argc <= 2) {
        printf("Usage: %s decimalcode bcm_pin [protocol] [pulselength] [repeattransmit]\n", argv[0]);
        printf("decimalcode\t- As decoded by RFSniffer\n");
        printf("bcm_pin\t- BCM GPIO PIN of connected transmiter\n");
        printf("protocol\t- According to rc-switch definitions\n");
        printf("pulselength\t- pulselength in microseconds\n");
        printf("repeattransmit\t- number of transmit repeat\n");
        return -1;
    }

    // Change protocol and pulse length accroding to parameters
    int code = atoi(argv[1]);
    int PIN = atoi(argv[2]);
    if (argc >= 4) protocol = atoi(argv[3]);
    if (argc >= 5) pulseLength = atoi(argv[4]);
    if (argc >= 6) repeatTransmit = atoi(argv[5]);
    if (argc >= 7) bitlength = atoi(argv[6]);
    
    if (wiringPiSetupGpio() == -1) return 1;
    RCSwitch mySwitch = RCSwitch();
    printf("%i|%i|%i\n", code,protocol,pulseLength);
    if (protocol != 1) mySwitch.setProtocol(protocol);
    if (pulseLength != 0) mySwitch.setPulseLength(pulseLength);
    if (repeatTransmit != 10) mySwitch.setRepeatTransmit(repeatTransmit);
    mySwitch.enableTransmit(PIN);
    mySwitch.send(code, bitlength);
    
    return 0;

}
