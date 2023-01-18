import random

from iotomatoes_supportpackage.MyThread import MyThread

noiseAmplitude = 1

class AmbientSimulator():
    def __init__(self):
        """Simulates the ambient. Initialize the values of the sensors 
        and the actuators"""

        self._temperature = 20
        self._humidity = 50
        self._light = 100
        self._soilMoisture = 50
        self._led = False
        self._pump = False

        self.UpdateThread = MyThread(self.update, 5)

    def stop(self):
        """Stop the thread that updates the values of the sensors"""
        self.UpdateThread.stop()

    def update(self):
        """Update the values of the sensors according 
            to the state of the actuators"""

        if self._led:
            self._light = 150 + 10*self.noiseValue()
        else:
            self._light = 40 + 10*self.noiseValue()

        if self._pump:
            self._soilMoisture += (2 + self.noiseValue())
            self._humidity += (1 + 0.2*self.noiseValue())
        else:
            self._soilMoisture -= (0.5 + self.noiseValue())
            self._humidity -= (0.1 + 0.1*self.noiseValue())

        self._temperature += (0.1 + 0.1*self.noiseValue())

    def get_temperature(self):
        return self._temperature + self.noiseValue()

    def get_humidity(self):
        return self._humidity + self.noiseValue()

    def get_light(self):
        return self._light + self.noiseValue()
    
    def get_soilMoisture(self):
        return self._soilMoisture + self.noiseValue()

    def noiseValue(self):
        """Return a random value between -noiseAmplitude and noiseAmplitude"""
        
        return  random.uniform(-noiseAmplitude, noiseAmplitude)

    def setActuator(self, actuator : str, state : bool):
        """Set the state of the actuator"""

        if actuator == "led":
            self._led = state
        elif actuator == "pump":
            self._pump = state
        else:
            print("Actuator not valid")