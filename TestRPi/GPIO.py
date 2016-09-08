


def __init__(self):
    print('GPIO Activated')

def setmode(mode):
    print(mode)

def setup(pin, inorout):
    print('%s set as %s' %(pin, inorout))

def IN():
    msg = 'Input'
    return msg

def OUT():
    msg = 'Output'
    return msg

def BCM():
    msg = 'BCM numbering selected'
    return msg

def cleanup():
    print('Cleaned up GPIO')


class PWM():

    def __init__(self, pin, frequency):
        print('pwm initialized on %s at %s Hz' % (pin, frequency))

    def start(self,duty):
        print('pwm at duty of %s' % duty)

    def stop(self):
        print('pwm stopped')

    def ChangeFrequency(self,frequency):
        print('Frequency changed to %s' % frequency)

    def ChangeDutyCycle(self,dc):
        print('Duty Cycle changed to %s' % dc)