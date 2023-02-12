import random

from .MyThread import MyThread

noiseAmplitude = 1


class AmbientSimulator():
    def __init__(self):
        """Simulates the ambient. Initialize the values of the sensors 
        and the actuators"""

        self._temperature = 20
        self._humidity = 50
        self._light = 50000
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
            self._light = self._light + 1000 + 100*self.noiseValue()
        else:
            self._light = self._light - 1000 - 100*self.noiseValue()

        if self._pump:
            self._soilMoisture += (0.5 + 0.02*self.noiseValue())
            self._humidity += (0.1 + 0.02*self.noiseValue())
        else:
            self._soilMoisture -= (0.05 + 0.01*self.noiseValue())
            self._humidity -= (0.01 + 0.01*self.noiseValue())

        self._temperature += (0.1 + 0.1*self.noiseValue())

        self._soilMoisture = self.saturate(self._soilMoisture, 0, 100)
        self._humidity = self.saturate(self._humidity, 0, 100)
        self._light = self.saturate(self._light, 10, 100000)

    def saturate(self, value, min, max):
        """Saturate the value between min and max"""
        if value > max:
            value = max
        elif value < min:
            value = min
        return value

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

        return random.uniform(-noiseAmplitude, noiseAmplitude)

    def setActuator(self, actuator: str, state: bool):
        """Set the state of the actuator"""

        if actuator == "led":
            self._led = state
        elif actuator == "pump":
            self._pump = state
        else:
            print("Actuator not valid")
