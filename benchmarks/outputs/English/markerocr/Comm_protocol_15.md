## **Flow of the CAN Protocol for Object Detection and Braking System**

### 1. **Object Detection Module**

- Detects obstacles and sets the Object\_Detected signal when an obstacle is within a threshold.
- Transmits the signal using the CAN protocol.

#### 2. **CAN Transmitter (TX) Module**

- Encodes the Object\_Detected signal into a CAN frame.
- Sends the CAN frame over the bus.

#### 3. **CAN Bus (Simulation in SystemVerilog)**

○ Transfers the CAN frame from the transmitter to the receiver.

## 4. **CAN Receiver (RX) Module**

- Decodes the received CAN frame.
- Extracts the Object\_Detected signal.

## 5. **Braking System Module**

- Receives the Object\_Detected signal.
- Activates braking if Object\_Detected is asserted.

# **SystemVerilog Code for CAN Protocol and Object Detection Integration**

#### **1. Object Detection Module**

```
module ObjectDetection (
  input logic clk,
  input logic reset,
  input logic obstacle_in_range,
  output logic Object_Detected
);
  always_ff @(posedge clk or posedge reset) begin
     if (reset)
       Object_Detected <= 0;
     else
       Object_Detected <= obstacle_in_range;
  end
endmodule
```