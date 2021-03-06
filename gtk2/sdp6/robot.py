import nxt
from nxt.bluesock import BlueSock
from nxt.motor import Motor
from nxt.motor import get_tacho_and_state
#from nxt.motor import OutputState
#from bluetooth import BluetoothError
import threading
from time import sleep
import gc
import logging

class RobotNotFoundError(Exception):
    def __str__(self):
      return "Robot not Found"

class RobotConnectionError(Exception):
    def __init__(self, error=None):
      self.error = error
    
    def __str__(self):
      return "Bluetooth: "+str(self.error)

class Robot(object):
  
  LEFT_WHEEL  = 0x02 # port C
  RIGHT_WHEEL = 0x00 # port A
  KICKER      = 0x01 # port B
    
  DEFAULT_POWER = 80
  TURN_POWER    = 0.8
  
  BUZZER_HZ = 769
  
  KICK_DISTANCE = 90
  
  STATE_DISCONNECTED = -1
  STATE_IDLE         = 0
  STATE_UP           = 1
  STATE_DOWN         = 2
  STATE_RIGHT        = 3
  STATE_LEFT         = 4
  
  MAX_MOTOR_POWER = 127
  
  #NAME = "BrickAshley"
  NAME = "BrickAsh"
    
  def __init__(self, host=None):
    
    self.power = -1*self.DEFAULT_POWER
    self.address = host   
    self.state = self.STATE_DISCONNECTED
    
    self.log = logging.getLogger("Robot")
  
  def connect(self):
    self.log.info("Connecting ...")
    try:
      if self.address == None:
        self.brick = nxt.find_one_brick().connect()
      else:
        self.brick = BlueSock(self.address).connect()      
    except nxt.locator.BrickNotFoundError:
      raise RobotNotFoundError
    except Exception as error:
      raise RobotConnectionError(error)
        
    self.leftWhell = Motor(self.brick, self.LEFT_WHEEL)
    self.rightWhell = Motor(self.brick, self.RIGHT_WHEEL)
    self.kicker = Motor(self.brick, self.KICKER)
    self.log.info("Set up Motors")
    
    try:
      #self.kicker.turn(100, 100, brake=True)
      
      self.log.debug(self.__read_motor_state(self.KICKER))
      
    except Exception as error:
      self.log.error("kicker reset error: " + str(error))
    
    self.state = self.STATE_IDLE
    
    self.__get_info()
    self.log.info("Conected to {name}".format(name=self.name))
    
    self.buzz()
  
  def disconnect(self):
    try:
      self.brick = None
      #self.get_info_thread.stop()
      gc.collect()
    except:
      self.log.warning("Unsafe disconect")
    
    self.state = self.STATE_DISCONNECTED
  
  def get_name(self):
    self.__get_info()
    return self.name
  
  def set_name(self, name):
    self.brick.set_brick_name(name)
    self.disconnect()
    self.connect()
    self.__get_info()
  
  def set_power(self, value):
    if value < -1*self.MAX_MOTOR_POWER or value > self.MAX_MOTOR_POWER:
      raise ValueError("Power can only be +-127")
    else:
      self.power = value
      self.log.info("power set to: "+str(self.power))
  
  def get_power(self):
    return self.power
  
  def __get_info(self):
    #self.get_info_thread = threading.Timer(30, self.__get_info)
    #self.get_info_thread.start()
    self.name, self.host, self.signal_strength, self.user_flash = self.brick.get_device_info()
    self.battery = self.brick.get_battery_level()
    self.log.info(
          "Info: \n\tName: {name}" \
          "\n\tBT MAC: {host}\n\tBT signal: {signal}\n\t" \
          "Memory: {memory}\n\tBattery: {voltage}mV".format(name=self.name, host=self.host, \
          signal=self.signal_strength, memory=self.user_flash, voltage=self.battery)
          )
  
  def up(self):
    self.log.debug("go up")
    if self.state != self.STATE_UP:
      self.state = self.STATE_UP
      self.leftWhell.run(power=self.power)
      self.rightWhell.run(power=self.power)
  
  def down(self):
    self.log.debug("go down")
    if self.state != self.STATE_DOWN:
      self.state = self.STATE_DOWN
      self.leftWhell.run(power=-1*self.power)
      self.rightWhell.run(power=-1*self.power)
  
  def right(self, withBrake=False):
    self.log.debug("go right")
    if self.state != self.STATE_RIGHT:
      self.state = self.STATE_RIGHT
      self.leftWhell.run(power=self.power*self.TURN_POWER)
      if withBrake:
        self.rightWhell.brake()
      else:
        self.rightWhell.run(power=-self.power*self.TURN_POWER)
  
  def left(self, withBrake=False):
    self.log.debug("go left")
    if self.state != self.STATE_LEFT:
      self.state = self.STATE_LEFT
      if withBrake:
        self.leftWhell.brake()
      else:
        self.leftWhell.run(power=-self.power*self.TURN_POWER)
      self.rightWhell.run(power=self.power*self.TURN_POWER)
  
  def stop(self):
    self.log.debug("go stop")
    self.state = self.STATE_IDLE
    self.leftWhell.brake()
    self.rightWhell.brake()
  
  def buzz(self):
    self.log.debug("buzz")
    self.brick.play_tone_and_wait(self.BUZZER_HZ, 1000)
  
  def kick(self):
    self.log.debug("kick")
    self.kicker.turn(-127, self.KICK_DISTANCE, brake=True)
    threading.Timer(1.5, self.__kick_reset).start()
  
  def __kick_reset(self):
    self.kicker.turn(127, self.KICK_DISTANCE, brake=True)
  
  #def __del__(self):
  #  self.log.debug("__del__")
  #  if self.brick != None:
  #    self.disconnect()
  
  def __read_motor_state(self, port):
    values = self.brick.get_output_state(port)
    self.log.debug("__read_motor_state: values='{0}'".format(values))
    #state, tacho = get_tacho_and_state(values)
    #self.log.debug("__read_motor_state: state='{0}', tacho='{1}'".format(state, tacho))
    left, kick, right = values[-3:]
    
    if port == self.KICKER:
      return kick
    elif port == self.LEFT_WHEEL:
      return left
    elif port == self.RIGHT_WHEEL:
      return left
    else:
      raise Exception("meh")
  
  def get_state(self):
    self.__read_motor_state(self.KICKER)
    self.__read_motor_state(self.LEFT_WHEEL)
    self.__read_motor_state(self.RIGHT_WHEEL)
  
  def kick_to(self, angle, kpower=127, withBrake=True):
    state, tacho = self.__read_motor_state(self.KICKER)
    if angle < tacho:
      self.kicker.turn(-kpower, tacho-angle, brake=withBrake)
    else:
      self.kicker.turn(+kpower, angle-tacho, brake=withBrake)

if __name__ == "__main__":
  print "Canot be run as main"


