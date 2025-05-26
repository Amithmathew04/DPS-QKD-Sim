import random
import math

class OpticalChannel:
    def __init__(self, distance_km, attenuation_db_per_km=0.2):
        self.distance_km = distance_km
        self.attenuation_db_per_km = attenuation_db_per_km
        self.survival_probability = 10**(-(self.distance_km * self.attenuation_db_per_km) / 10)

    def transmit_pulse(self, photon_count):
        received_photons = 0
        for _ in range(photon_count):
            if random.random() < self.survival_probability:
                received_photons += 1
        return received_photons

class MachZehnderInterferometer:
   
    def __init__(self, ideal_split_ratio=0.5):
        self.ideal_split_ratio = ideal_split_ratio

    def interfere_pulses(self, phase_n_minus_1, phase_n):
        delta_phi = (phase_n - phase_n_minus_1) % (2 * math.pi)
        
       
        if delta_phi > math.pi:
            delta_phi -= 2 * math.pi
        elif delta_phi < -math.pi:
            delta_phi += 2 * math.pi

        
        prob_dm1 = math.cos(delta_phi / 2)**2
        
        prob_dm2 = math.sin(delta_phi / 2)**2
        
        return prob_dm1, prob_dm2

class SinglePhotonDetector:
    def __init__(self, quantum_efficiency=0.9, dark_count_rate_per_ns=1e-9, time_window_ns=1):
        self.quantum_efficiency = quantum_efficiency 
        self.dark_count_rate = dark_count_rate_per_ns
        self.time_window = time_window_ns 
        
        self.prob_dark_count_per_window = self.dark_count_rate * self.time_window

    def detect(self, incident_photons):
        click = False
        
        if incident_photons > 0:
            prob_actual_detection = 1 - (1 - self.quantum_efficiency)**incident_photons
            if random.random() < prob_actual_detection:
                click = True
        
        if not click: 
             if random.random() < self.prob_dark_count_per_window:
                 click = True
                 
        return click 

class Receiver:
    
    def __init__(self, detector_efficiency=0.9, dark_count_rate=1e-9):
        self.mzi = MachZehnderInterferometer()
        self.detector_dm1 = SinglePhotonDetector(detector_efficiency, dark_count_rate)
        self.detector_dm2 = SinglePhotonDetector(detector_efficiency, dark_count_rate)
        self.raw_clicks_info = [] 
        self.bob_raw_key_bits = [] 
        
    def receive_and_measure(self, time_slot, current_pulse_photons, current_pulse_phase, 
                            previous_pulse_photons, previous_pulse_phase):
        
        if previous_pulse_photons == 0 or current_pulse_photons == 0:
            incident_photons_dm1_effective = 0
            incident_photons_dm2_effective = 0
        else:
            prob_dm1_ideal, prob_dm2_ideal = self.mzi.interfere_pulses(
                previous_pulse_phase, current_pulse_phase
            )
            
            
            effective_incoming_photons = min(current_pulse_photons, previous_pulse_photons)
            if effective_incoming_photons > 0: 
                incident_photons_dm1_effective = round(effective_incoming_photons * prob_dm1_ideal)
                incident_photons_dm2_effective = round(effective_incoming_photons * prob_dm2_ideal)
            else:
                incident_photons_dm1_effective = 0
                incident_photons_dm2_effective = 0


        
        click_dm1 = self.detector_dm1.detect(incident_photons_dm1_effective)
        click_dm2 = self.detector_dm2.detect(incident_photons_dm2_effective)

        measured_phase_diff = None
        if click_dm1 and not click_dm2:
            measured_phase_diff = 0.0 
            bob_bit = 0
        elif click_dm2 and not click_dm1:
            measured_phase_diff = math.pi 
            bob_bit = 1
        elif click_dm1 and click_dm2:
            if prob_dm1_ideal > prob_dm2_ideal:
                measured_phase_diff = 0.0
                bob_bit = 0
            else:
                measured_phase_diff = math.pi
                bob_bit = 1
            print(f"Warning: Ambiguous click at time {time_slot}. Both DM1 and DM2 clicked.")
        else: 
            measured_phase_diff = None
            bob_bit = None 

        self.raw_clicks_info.append({
            'time_slot': time_slot,
            'click_dm1': click_dm1,
            'click_dm2': click_dm2,
            'measured_phase_diff': measured_phase_diff,
            'bob_inferred_bit': bob_bit
        })
        
        return click_dm1, click_dm2, measured_phase_diff, bob_bit
