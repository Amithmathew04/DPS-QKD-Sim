# dps_qkd_source.py
from bitstring import Bits
import random
import math

class LightSource:
    
    def __init__(self, average_photon_number=0.2):
        if not (0 < average_photon_number < 1):
            raise ValueError("Average photon number (mu) for WCP should be between 0 and 1.")
        self.mu = average_photon_number 

    def generate_single_pulse_photon_count(self):
        num_photons = 0
        L = math.exp(-self.mu)
        p = 1.0
        k = 0
        while p > L:
            k += 1
            p *= random.random()
        num_photons = k - 1
        return num_photons

    def get_initial_phase(self):
       
        return 0.0 

class PhaseModulator:
    
    def modulate_phase(self, current_phase, desired_phase_shift):
        return (current_phase + desired_phase_shift) % (2 * math.pi)

class Sender:
   
    def __init__(self, avg_photon_number=0.2):
        self.light_source = LightSource(avg_photon_number)
        self.phase_modulator = PhaseModulator()
        self.raw_key_bits = [] 
        self.sent_pulses_info = [] 

    def prepare_secret_bit(text):
        bit_list = [bit for char in text for bit in Bits(uint=ord(char), length=8).bin]
        return bit_list


    def prepare_and_send_pulse(self, time_slot, previous_pulse_phase=0):

        current_secret_bit = random.randint(0, 1) 
        self.raw_key_bits.append(current_secret_bit)
        desired_phase_difference_for_bit = 0.0 if current_secret_bit == 0 else math.pi
        
        modulated_phase_on_this_pulse =  (previous_pulse_phase + desired_phase_difference_for_bit) % (2 * math.pi)
        
        photon_count = self.light_source.generate_single_pulse_photon_count()
        
        self.sent_pulses_info.append({
            'time_slot': time_slot,
            'photon_count': photon_count,
            'modulated_phase': modulated_phase_on_this_pulse,
            'alice_intended_bit_for_pair': current_secret_bit 
        })
        
        return modulated_phase_on_this_pulse, photon_count

    def get_pulse_info(self, time_slot):
        for pulse_info in self.sent_pulses_info:
            if pulse_info['time_slot'] == time_slot:
                return pulse_info
        return None
    
