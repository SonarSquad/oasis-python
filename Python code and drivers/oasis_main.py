

# ---------- Imports for Plotting ------------------------------------
import matplotlib.pyplot as plt
from matplotlib.pyplot import ion, show

# ---------- Other imports -------------------------------------------
import math
import time
import RPi.GPIO as GPIO
from subprocess import Popen, PIPE
from scipy.fft import fft


# --------------------- FUNCTIONS ------------------------------------------------------------------------------------------------------

def get_ADC_data(): 
    # This function initiates a process and 
    # returns a list with 1.7 million voltage readings taken at 1.7MHz sampling frequency.
    # The sampling frequency and number of samples taken can adjusted in the C-driver (max = 1.7MHz @ 2M samples)
    # The compiled and executable C-code needs to be in the same directory as this python file.  

    Vref = 4.096 # Reference voltage used in the ADC. 4.096 for internal reference ADS8422 

    # Start a subprocess: call the C code and let it run to do a parallel ADC read. 
    c_process = Popen("./oasis_read_ADC_parallel", stdin = PIPE, stdout = PIPE)
    OUTS, errs = c_process.communicate()

    """
    -----------------------------------------------------------------------------------------------------------------------------------------
    Now the variable "OUTS" (bytes object) contains a list with the states of the GPIO register after each ADC sample.
    - Each entry in the list is an integer. 
    - Each integer represents a 32-bit register read.
    -----------------------------------------------------------------------------------------------------------------------------------------
    # The rest of this function converts the list of integers received from the C code into a list with voltages. 
     ----------------------------------------------------------------------------------------------------------------------------------------
    2. Convert integers to 32-bit bit-string.
    3. Manipulate string in order to extract the bits representing the GPIOs physically connected to the data lines of ADC.
    4. Sort the manipulated bits so that they have the right place in a 16-bit string. 
    5. Convert the 16-bit string to voltage reading - remember 16-bit value is two's complement.   
    -----------------------------------------------------------------------------------------------------------------------------------------
    """    

    data = OUTS.decode('UTF-8')               # Decode outs from byte-object and make a python string
    data_list_string = data.split(',')        # Split the string at comma and put all entries into a new python list 
    number_of_samples = len(data_list_string) # Get the total number of samples 
    
    data_list_int = list(map(int, data_list_string)) # Convert string-entries to integers 

    bit32_list_string = [0]*number_of_samples   # Preallocating list
    for i in range(0,number_of_samples):        # Convert integers from data_list_int to bit-string of 32 bit length. 
        bit32_list_string[i] = ('{0:032b}'.format(data_list_int[i]))  

    bit16_list_string = [0]*number_of_samples   # Preallocating list 
    for i in range(0,number_of_samples):        # Extract bit position for the 16 GPIOs of interest from 32-bit bit-string. 
        bits = bit32_list_string[i]      
        #                    ADC-bit = RaspberryPi            index = (31 - GPIO)
        bit0  = bits[17]   # bit 0 =  GPIO 14       bit32_list_string  index 17
        bit1  = bits[16]   # bit 1 =  GPIO 15       bit32_list_string  index 16 
        bit2  = bits[13]   # bit 2 =  GPIO 18       bit32_list_string  index 13
        bit3  = bits[8]    # bit 3 =  GPIO 23       bit32_list_string  index 8 
        bit4  = bits[7]    # bit 4 =  GPIO 24       bit32_list_string  index 7 
        bit5  = bits[6]    # bit 5 =  GPIO 25       bit32_list_string  index 6 
        bit6  = bits[23]   # bit 6 =  GPIO 8        bit32_list_string  index 23 
        bit7  = bits[24]   # bit 7 =  GPIO 7        bit32_list_string  index 24 
        bit8  = bits[19]   # bit 8 =  GPIO 12       bit32_list_string  index 19 
        bit9  = bits[15]   # bit 9 =  GPIO 16       bit32_list_string  index 15 
        bit10 = bits[11]   # bit 10 = GPIO 20       bit32_list_string  index 11 
        bit11 = bits[10]   # bit 11 = GPIO 21       bit32_list_string  index 10 
        bit12 = bits[5]    # bit 12 = GPIO 26       bit32_list_string  index 5 
        bit13 = bits[12]   # bit 13 = GPIO 19       bit32_list_string  index 12 
        bit14 = bits[18]   # bit 14 = GPIO 13       bit32_list_string  index 18 
        bit15 = bits[25]   # bit 15 = GPIO 6        bit32_list_string  index 25 

        # Format 16-bit string: bit16_list_string[0] = MSB, bit16_list_string[15] = LSB
	    # Two's complement representation 
        bit16_list_string[i] = (bit15 + bit14 + bit13 + bit12 + bit11 + bit10 + bit9 + bit8 + bit7 + bit6 + bit5 + bit4 + bit3 + bit2 + bit1 + bit0)
    


    bit16_list_int = [0]*number_of_samples
    for i in range(0, number_of_samples):                   # Convert bit string back to integer 
        bit16_list_int[i] = int(bit16_list_string[i],2)     
    
        if bit16_list_int[i] > 32767:                       # Convert from two's complement   2**15-1 = 32767
            bit16_list_int[i] = -65536 + bit16_list_int[i]

    ADC_list_voltage = [0]*number_of_samples                # Convert ADC bit-data to voltage reading
    for i in range(0, number_of_samples):
        ADC_list_voltage[i] = (Vref) * (bit16_list_int[i] / (2**15))
    
    # The list: ADC_list_voltage now contains all samples presented as voltage.   
    return ADC_list_voltage

# --------------------------------- END FUNCTION ------------------------------------------------------------------------------------------

#--------------------------------------SETUP ----------------------------------------------------------------------------------------------
# The ADS8422 Driver needs to be in the same folder as this oasis_main.py script. 
# Before running the main code the C driver needs to be compiled. 
# In order to compile the C driver run the following in terminal:
# gcc oasis_ADS8422_ADC_parallel.c.c -o  oasis_ADS8422_ADC_parallel.c

# Following connections are made between the ADS8422 ADC Board and RaspberryPi: 
# CONVST = GPIO 4
# BUSY = GPIO 3
# RD = GPIO 17 
# CS = connect to LOW        (GND)
# BYTE = connect to LOW      (GND)
# RESET = connect to HIGH   (3.3v)
# PD2 = connect to HIGH     (3.3v) 
# Connect GPIO 1 and GPIO 0 to the MCU 

sampling_frequency = 1700000

GPIO.setmode(GPIO.BCM)
GPIO.setup(1, GPIO.OUT) # GPIO 1 used for communication Raspberry --> MCU 
GPIO.setup(0, GPIO.IN)  # GPIO 0 used for communication MCU --> Raspberry
RUN = True 

# ----------------------------------- MAIN LOOP -------------------------------------------------------------------------------------------
while RUN == True:
	
    GPIO.output(1,1) # Pulse pin 1 to in order to trigger MCU to start chirping. 
    GPIO.output(1,0) 
	
    while GPIO.input(0) == HIGH: 
        # Wait for MCU to pull it's interface wire low. LOW signals indicates chirping done.  
 
    voltage_list = get_ADC_data() # start sampling the returning echo signal
    number_of_samples = len(voltage_list)

    command_FFT = input("Plot FFT?  Y/N: ") # User input through terminal 
    if command_FFT == "Y": # Set up and plot FFT: 
        N = number_of_samples
        
        x_vect = [0] * N    # Set up a frequency vector for the x-axis of plot       
        for i in range(0, N):
	        x_vect[i] = (i * (sampling_frequency/N))/1000   # Divide by 1000 to get KHz along X axis  
        

        fft_data = fft(voltage_list, N) # Take the FFT of the original voltage data
        FFT_abs = abs(fft_data) # Absolute value 
        FFT_scaled = ((FFT_abs / N) * 2)  # Scaled and multiplied by 2 - only one mirrored part valid in FFT.
        ion() 
        plt.figure(1)
        plt.style.use('seaborn-whitegrid')
        plt.plot(x_vect, FFT_scaled, color ='red', linewidth=1)
        plt.title('FFT of sampled signal')
        plt.xlabel('Frequency KHz')
        plt.ylabel('Magnitude')
        plt.tight_layout()
        plt.show() 
        
    
    command_PLOT = input("Plot voltage vs. time?  Y/N: ") # User input through terminal 
    if command_PLOT == "Y":                               # Plot data                  
        samples = [0]*number_of_samples 
        for i in range(0, number_of_samples): # set up sample number vector for x-axis 
            samples[i] = i
        ion()
        plt.figure(2)
        plt.style.use('seaborn-whitegrid')
        plt.plot(samples, voltage_list, color ='red', linewidth=1)
        plt.title('Plotting of ADC voltage data')
        plt.xlabel('Sample nbr.')
        plt.ylabel('voltage difference between inputs')
        plt.tight_layout()
        plt.show()


    command_SAVE = input("Save voltage samples to .txt file? Y/N: ") # User input through terminal 
    if command_SAVE == "Y":                                          # Save sampled data to a .txt file 
        file_name_input_str = input("Insert filename: ")
        file_name_str = file_name_input_str + ".txt"
        
        file_object = open(file_name_str, "w+")
        file_object.write(str(voltage_list))
        print("SUCCESS! Sampling-session saved as:", file_name_str)

    RUN = False 

