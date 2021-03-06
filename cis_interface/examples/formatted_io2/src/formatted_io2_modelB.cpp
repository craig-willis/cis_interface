#include <iostream>
// Include methods for input/output channels
#include "CisInterface.hpp"

#define MYBUFSIZ 1000

int main(int argc, char *argv[]) {
  // Initialize input/output channels
  CisAsciiTableInput in_channel("inputB");
  CisAsciiTableOutput out_channel("outputB", "%6s\t%d\t%f\n");

  // Declare resulting variables and create buffer for received message
  int flag = 1;
  char name[MYBUFSIZ];
  int count = 0;
  double size = 0.0;

  // Loop until there is no longer input or the queues are closed
  while (flag >= 0) {
  
    // Receive input from input channel
    // If there is an error, the flag will be negative
    // Otherwise, it is the size of the received message
    flag = in_channel.recv(3, &name, &count, &size);
    if (flag < 0) {
      std::cout << "Model B: No more input." << std::endl;
      break;
    }

    // Print received message
    std::cout << "Model B: " << name << ", " << count << ", " << size << std::endl;

    // Send output to output channel
    // If there is an error, the flag will be negative
    flag = out_channel.send(3, name, count, size);
    if (flag < 0) {
      std::cout << "Model B: Error sending output." << std::endl;
      break;
    }

  }
  
  return 0;
}
