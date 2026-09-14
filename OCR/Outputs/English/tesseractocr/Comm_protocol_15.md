Flow of the CAN Protocol for Object Detection and Braking System

1. Object Detection Module

o Detects obstacles and sets the 0b ject_Detected signal when an obstacle is
within a threshold.
o Transmits the signal using the CAN protocol.
2. CAN Transmitter (TX) Module

o Encodes the Object_Detected signal into a CAN frame.
o Sends the CAN frame over the bus.
3. CAN Bus (Simulation in SystemVerilog)

o Transfers the CAN frame from the transmitter to the receiver.
4. CAN Receiver (RX) Module

o Decodes the received CAN frame.
o Extracts the Object_Detected signal.
5. Braking System Module

o Receives the Object_Detected signal.
o Activates braking if 0b ject_Detected is asserted.

SystemVerilog Code for CAN Protocol and Object Detection Integration

1. Object Detection Module
module ObjectDetection (
input logic clk,
input logic reset,
input logic obstacle_in_range,
output logic Object_Detected

always_ff @(posedge clk or posedge reset) begin
if (reset)
Object_Detected <= 0;
else
Object_Detected <= obstacle_in_range;
end
endmodule

