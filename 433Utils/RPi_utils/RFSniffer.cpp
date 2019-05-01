/*
  RFSniffer

  Usage: ./RFSniffer bcm_pin [tolerance] [<pulseLength>]
  [] = optional

  Printf: Received code | Protocol | Pulse lenght | BitLength
  Hacked from http://code.google.com/p/rc-switch/
  by @justy to provide a handy RF code sniffer
*/

#include "../rc-switch/RCSwitch.h"
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
     
RCSwitch mySwitch;
 
int main(int argc, char *argv[]) {
  
     if (argc == 1) {
       printf("Usage: %s bcm_pin [<pulseLength>]\n", argv[0]);
       return 0;
     }
     if(wiringPiSetupGpio() == -1) {
       printf("wiringPiSetup failed, exiting...");
       return 0;
     }
     int PIN = atoi(argv[1]);
     int pulseLength = 0;
     int tolerance = 60;
     if (argv[2] != NULL) tolerance = atoi(argv[2]);
     if (argv[3] != NULL) pulseLength = atoi(argv[3]);

     mySwitch = RCSwitch();
     if (tolerance != 60) mySwitch.setReceiveTolerance(tolerance);
     if (pulseLength != 0) mySwitch.setPulseLength(pulseLength);
     mySwitch.enableReceive(PIN); 
     
    
     while(1) {
  
      if (mySwitch.available()) {
        int value = mySwitch.getReceivedValue();
        if (value == 0) {
          printf("Unknown encoding\n");
        } else {    
          printf("%i|%i|%i|%i\n", mySwitch.getReceivedValue(),mySwitch.getReceivedProtocol(),mySwitch.getReceivedDelay(),mySwitch.getReceivedBitlength() );
          // printf("Received %i\n", mySwitch.getReceivedValue() );
          // printf("Bit lenght %i\n", mySwitch.getReceivedBitlength() );
          // printf("Protocol %i\n", mySwitch.getReceivedProtocol() );
          // printf("Delaye %i\n", mySwitch.getReceivedDelay() );
          // printf("Raw data %i\n", mySwitch.getReceivedRawdata() );
        }
    
        fflush(stdout);
        mySwitch.resetAvailable();
      }
      usleep(10000); 
  
  }

  exit(0);


}

