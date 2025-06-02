from machine import Pin, SPI
import time
import random


# Assign chip select (CS) pin and initialize it high
a0 = Pin(14, Pin.OUT)	#OPL3	14
a1 = Pin(15, Pin.OUT)	#OPL3	15
latch = Pin(17, Pin.OUT)#OPL3	17
reset = Pin(16, Pin.OUT)#OPL3 initiel clear
shift_latch = Pin(22, Pin.OUT)#shift register
load = Pin(28, Pin.OUT)	#shift register - buttons
cs1 = Pin(5, Pin.OUT)	#shift register - buttons
adc1 = machine.ADC(26)    #analog multiplexer - potentiometrs and keys
A2 = Pin(8, Pin.OUT)    #analog multiplexer
B2 = Pin(9, Pin.OUT)    #analog multiplexer
C2 = Pin(10, Pin.OUT)    #analog multiplexer
A3 = Pin(11, Pin.OUT)    #analog multiplexer
B3 = Pin(12, Pin.OUT)    #analog multiplexer
C3 = Pin(13, Pin.OUT)    #analog multiplexer


arr_byte = bytearray([0x50,0x70,0x60,0x05,0x06,0x40,0x10,0x20,0x07,0x04,   0x34,0x36,0x37,0x35,0x33,0x30,0x31,0x32,0x03,0x02,0x01,0x00]) #hodnoty pro cteni analogovych vstupu pomoci multiplexeru. dolni cislice jsou "nizsi multiplexer" - takze nejdriv napsat adresu vyssiho multiplexeru, pak nizsi. nejdriv cteni potenciometru, pak keys
arr_analog_pot = [0, 0, 0, 0, 0 ,0 , 0, 0, 0, 0]		#contains analog values of 10 potentiometers located on board "left to right, up to down"
arr_analog_key = [0, 0, 0, 0, 0 ,0 , 0, 0, 0, 0, 0, 0]	#contains analog values of 12 keys located on board "left to right"
arr_analog_key_compare = [200, 220, 200, 200, 200 ,200 , 200, 200, 200, 200, 200, 200]	#threshold values of keys - to determine if key is pressed
arr_key = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]	#states of keys - true if pressed

attack = 0
decay = 0
sustain = 0
relase = 0
feedback = 0
frequency_block = 4 #can be used to select octave
waveform = 1
arr_notes = [345, 365, 387, 410, 434 ,460 , 487, 516, 547, 580, 614, 651, 0, 0, 0, 0, 0, 0]	#note frequency number select for each key

array2 = [0, 0, 0, 0, 0, 0, 0, 0, 6, 5, 7, 0, 3, 2, 1, 0, ]

rx_buttons = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
rx_buttons_previous = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
arr_byte_but = bytearray([0b0010_1000,0b0011_1000,0b0011_0000,0b0000_0101,0b0000_0110])

#Two-operator Melodic mode - offsety pro jednotlive kanaly
# --------------------------------------------------
#  Channel    0     1      2     3     4     5     6     7     8     9     10    11    12    13    14    15    16    17
#  Operator 1 00    01     02    06    07    08    12    13    14    18    19    20    24    25    26    30    31    32      
#  Operator 2 03    04     05    09    10    11    15    16    17    21    22    23    27    28    29    33    34    35      
op1_offset = [0x00, 0x01, 0x02, 0x06, 0x07, 0x08, 0x0C, 0x0D, 0x0E, 0x12, 0x13, 0x14, 0x18, 0x19, 0x1A, 0x1E, 0x1F, 0x20]
op2_offset = [0x03, 0x04, 0x05, 0x09, 0x0A, 0x0B, 0x0F, 0x10, 0x11, 0x15, 0x16, 0x17, 0x1B, 0x1C, 0x1D, 0x21, 0x22, 0x23]

    # Initialize SPI //data=mosi shift=sck
spi1 = SPI(0,		#for button read
          baudrate=400000,
          polarity=0,
          phase=0,
          bits=8,
          firstbit=SPI.MSB,
          sck=Pin(2),
          mosi=Pin(3),
          miso=(4))

spi = SPI(0,	#for OPL3
        baudrate=400000,
        polarity=0,
        phase=0,
        bits=8,
        firstbit=SPI.MSB,
        sck=Pin(18),
        mosi=Pin(19))

reset = Pin(16, Pin.OUT)#must be here because micropython, OPL3 reset pin
    
latch.value(1)
reset.value(1)
a0.value(0)
a1.value(0)
    
def opl_reset():
    reset.value(0)
    time.sleep_ms(1)
    reset.value(1) #clear registers of OPL2.
    time.sleep_ms(1)


def opl3_write(register, low_value, high_value): #low_value = value of "lower" register
    a1.value(0)
    a0.value(0)  # Set A0, A1 low to indicate it's a lower register address
    spi.write(bytearray([register]))
    latch.value(0)
    latch.value(1)  # Latch the lower register address
        
    a0.value(1)  # Set A0 high to indicate it's data
    spi.write(bytearray([low_value]))
    latch.value(0)
    latch.value(1)  # Latch the data to lower register
    
    a0.value(0)    
    a1.value(1)# Set A0 low and A1 high to indicate it's a higher register address
    spi.write(bytearray([register]))
    latch.value(0)
    latch.value(1)  # Latch the higher register address

    a0.value(1)  # Set A0 high to indicate it's data, A1 dont care
    spi.write(bytearray([high_value]))
    latch.value(0)
    latch.value(1)  # Latch the data to higher register
    a1.value(0)

def opl3_init(frequency, offset): #channel offset, frequency select
    opl3_write(0x04, 0x00, 0x00)  # Set 4 op mode to 0
    opl3_write(0x05, 0x00, 0x01)  # Set to opl3 mode
    opl3_write(0x20 + offset, 0xa9, 0xa4)  # Set operator 1 frequency multiplier
    opl3_write(0x40 + offset, 0x02, 0x00)  # Set operator 1 level
    opl3_write(0x60 + offset, 0x44, 0x76)  # Set operator 1 amplitude envelope parameters
    opl3_write(0x80 + offset, 0xe5, 0x20)  # Set operator 1 amplitude envelope parameters
    opl3_write(0x23 + offset, 0x07, 0x0f)  # Set the carrier's multiple to 1
    opl3_write(0xa0 + offset, 0x00 + frequency, 0x00 + frequency)  # Set frequency number
    opl3_write(0x43 + offset, 0x04, 0x04)  # Set the carrier to maximum volume (about 47 dB)
    opl3_write(0x63 + offset, 0x30, 0x30)  # Carrier attack:  quick;   decay:   long
    opl3_write(0x83 + offset, 0x33, 0x33)  # Carrier sustain: medium;  release: medium
    opl3_write(0xe3 + offset, 0x01, 0x03)  #
    #opl3_write(0xe0, 0x00, 0x01)  # 
    opl3_write(0xb0 + offset, 0x22, 0x22)  # Turn the voice on; set the octave and freq MSB
    opl3_write(0xc0 + offset, 0xf0, 0xf0)  # feedback , algoritmh
    opl3_write(0xbd + offset, 0x00, 0x00)
    #opl3_write(0xE0 + offset, 0xc0, 0xc0)
    #time.sleep(0.2)
    
    
def opl3_play(op1_offset, op2_offset, key , frequency, num): #operator offsets, key on , frequency select, array index
    if 1:
        opl3_write(0x20 + op1_offset, 0x06, 0x04)  # Set operator tremolo, vibrato, sus, KSR, op 1 frequency multiplier
        opl3_write(0x40 + op1_offset, 0b0111_1000, 0b0111_1000)  # Set operator 1 key scale level, attenuation
        opl3_write(0x60 + op1_offset, (attack<<4) | decay, (attack<<4) | decay)  # Set operator amplitude envelope parameters
        opl3_write(0x80 + op1_offset, (sustain<<4) | relase, (sustain<<4) | relase)  # Set operator amplitude envelope parameters
    
        opl3_write(0x20 + op2_offset, 0x02, 0x02)  # Set the carrier's multiple to 1
        opl3_write(0x40 + op2_offset, 0x00, 0x00)  # Set the carrier to maximum volume (about 47 dB)
        opl3_write(0x60 + op2_offset, (attack<<4) | decay, (attack<<4) | decay)  # Carrier attack:  quick;   decay:   long
        opl3_write(0x80 + op2_offset, (sustain<<4) | relase, (sustain<<4) | relase)  # Carrier sustain: medium;  release: medium
    
        opl3_write(0xe0 + op1_offset, waveform, waveform)  #
        opl3_write(0xe0 + op2_offset, waveform, waveform)  #

def opl3_key_on():
    for num in range(9):
        opl3_write(0xa0 + num, ((arr_notes[num]<<2)>>2), 									((arr_notes[num+9]<<2)>>2))  # Set frequency number
        opl3_write(0xb0 + num, (arr_key[num]<<5)+(frequency_block<<2)+(arr_notes[num]>>8), 	(arr_key[num+9]<<5)+(frequency_block<<2)+(arr_notes[num]>>8))  # Turn the voice on; set the octave and freq MSB
        opl3_write(0xc0 + num, (0b11110000 + (feedback<<1)), 								(0b11110000 + (feedback<<1)))  # feedback , algoritmh
        
def analog_read():
    global attack, decay, sustain, relase, feedback
    for x in range(10):		#reads potentiometer values
        idk = arr_byte[x]
        A2.value(idk & 0b0000_0001)
        B2.value(idk & 0b0000_0010)
        C2.value(idk & 0b0000_0100)
        A3.value(idk & 0b0001_0000)
        B3.value(idk & 0b0010_0000)
        C3.value(idk & 0b0100_0000)
        time.sleep_us(1)
        arr_analog_pot[x] = adc1.read_u16()>>8
        
    for x in range(12):		#reads keys analog values
        idk = arr_byte[x+10]
        A2.value(idk & 0b0000_0001)
        B2.value(idk & 0b0000_0010)
        C2.value(idk & 0b0000_0100)
        A3.value(idk & 0b0001_0000)
        B3.value(idk & 0b0010_0000)
        C3.value(idk & 0b0100_0000)
        time.sleep_us(1)
        arr_analog_key[x] = adc1.read_u16()>>8
        if arr_analog_key[x] > arr_analog_key_compare[x]:
            arr_key[x] = 0
        else:
            arr_key[x] = 1
            
           
    attack = arr_analog_pot[0] >> 4
    decay = arr_analog_pot[1] >> 4
    sustain = arr_analog_pot[2] >> 4
    relase 	= arr_analog_pot[3] >> 4
    feedback = arr_analog_pot[4] >> 5
            

def button_read():
    global waveform, frequency_block
    load.value(0); load.value(1)  # Single-line pulse
    cs1.value(0)
    data = spi1.read(2, 0x00)
    cs1.value(1)
    button_mask = [0xfffe, 0xfffd, 0xfffb, 0xfff7, 0xff7f, 0xffbf, 0xffdf, 0xfeff, 0xfdff, 0xfbff, 0xf7ff,0x7fff, 0xbfff, 0xffef, 0xdfff, 0xefff]
    data_int = int.from_bytes(data, 'big')
    for x in range(16):
        rx_buttons[x] = (data_int | button_mask[x])!=0xffff
        
    if rx_buttons[0]==1 and rx_buttons_previous[0]==0:
        waveform = waveform+1
    if rx_buttons[1]==1 and rx_buttons_previous[1]==0:
        waveform = waveform-1
    if waveform < 0:
        waveform = 7
    if waveform > 7:
        waveform = 0
        
    if rx_buttons[2]==1 and rx_buttons_previous[2]==0:
        frequency_block = frequency_block+1
    if rx_buttons[3]==1 and rx_buttons_previous[3]==0:
        frequency_block = frequency_block-1
    if frequency_block < 0:
        frequency_block = 7
    if frequency_block > 7:
        frequency_block = 0
    #return [(int.from_bytes(data, 'big') >> (15 - i)) & 1 for i in range(16)]
    for x in range(16):
        rx_buttons_previous[x] = rx_buttons[x]


opl_reset()
opl3_init(0, 0)
opl3_init(0, 1)

while True:
    analog_read()
    button_read()
    #print(arr_analog_pot)
    print(arr_key)
    #print(feedback)
    #print(bin(0x20 | (rx_buttons[0] <<4) | (rx_buttons[1] <<3) | (rx_buttons[2] <<2) | (rx_buttons[3] <<1) | (rx_buttons[4])))
    #print(button_read())
#    print(rx_buttons)
    #print(bin((attack<<4) | decay))

    for num in range(12):
        opl3_play(op1_offset[num], op2_offset[num], arr_key[num] , arr_notes[num], num)
        #print(op1_offset[num], op2_offset[num], arr_key[num])
    opl3_key_on()
    
    print("0")    
    #time.sleep_us(200000)


