# PID controller algorithm



#pid controller
def PID_Output(kp,ki,kd,e1,e2,setpoint,mv)
  k1 = kp + ki + kd
  k2 = -ki - 2 * kd
  k3 = kd
  
  #update error variables
  e2 = e1
  e1 = e
  e = setpoint - mv
  
  delta_u = k1 * e + k2 * e1 + k3 * e2
  u = u + delta_u
  return u
  
  
