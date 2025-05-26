
from Source import Sender
from Hardware import Receiver, OpticalChannel

import math 

class Node:
    def __init__(self, node_id, avg_photon_number=0.2, detector_efficiency=0.9, dark_count_rate=1e-9):
        self.node_id = node_id
        self.qkd_sender = Sender(avg_photon_number)
        self.qkd_receiver = Receiver(detector_efficiency, dark_count_rate)
        self.connected_links = {}
        self.shared_keys = {}     
        self.traffic_log = []    

    def add_link(self, neighbor_node_id, channel_instance):

        self.connected_links[neighbor_node_id] = channel_instance

    def generate_and_share_key(self, target_node, num_pulses, pulse_repetition_rate_ns):
        
        print(f"--- Node {self.node_id} initiating QKD with Node {target_node.node_id} ---")
        
        
        self.qkd_sender = Sender(self.qkd_sender.light_source.mu)
        target_node.qkd_receiver = Receiver(target_node.qkd_receiver.detector_dm1.quantum_efficiency,
                                        target_node.qkd_receiver.detector_dm1.dark_count_rate)

        alice_pulses_sent_info = [] 
        previous_pulse_actual_phase = self.qkd_sender.light_source.get_initial_phase() 

        for i in range(num_pulses):
            time_slot = i * pulse_repetition_rate_ns
            modulated_phase, photon_count = self.qkd_sender.prepare_and_send_pulse(time_slot, previous_pulse_actual_phase)
            alice_pulses_sent_info.append(self.qkd_sender.get_pulse_info(time_slot)) 
            previous_pulse_actual_phase = modulated_phase 

        
        channel = self.connected_links.get(target_node.node_id)
        if not channel:
            raise ValueError(f"No channel defined between {self.node_id} and {target_node.node_id}")

        channel_processed_pulses = []
        for pulse in alice_pulses_sent_info:
            received_photons = channel.transmitted_pulse(pulse['photon_count'])
            channel_processed_pulses.append({
                'time_slot': pulse['time_slot'],
                'received_photon_count': received_photons,
                'modulated_phase': pulse['modulated_phase'] 
            })


        bob_clicks_and_inferred_bits = []
        
        dummy_prev_received_pulse = {'received_photon_count': 0, 'modulated_phase': 0.0}

        for i in range(len(channel_processed_pulses)):
            current_received_pulse = channel_processed_pulses[i]
            
            previous_received_pulse_for_mzi = dummy_prev_received_pulse if i == 0 else channel_processed_pulses[i-1]

            click_dm1, click_dm2, measured_phase_diff, bob_bit = target_node.qkd_receiver.receive_and_measure(
                current_received_pulse['time_slot'],
                current_received_pulse['received_photon_count'],
                current_received_pulse['modulated_phase'],
                previous_received_pulse_for_mzi['received_photon_count'],
                previous_received_pulse_for_mzi['modulated_phase']
            )
            bob_clicks_and_inferred_bits.append({
                'time_slot': current_received_pulse['time_slot'],
                'click_dm1': click_dm1,
                'click_dm2': click_dm2,
                'measured_phase_diff': measured_phase_diff,
                'bob_inferred_bit': bob_bit 
            })

        alice_sifted_key = []
        bob_sifted_key = []
        sifted_time_slots = []
        
        for i in range(1, len(alice_pulses_sent_info)):
            alice_pn_minus_1_info = alice_pulses_sent_info[i-1]
            alice_pn_info = alice_pulses_sent_info[i]
            
            bob_measurement_info_for_pn = None
            for click_info in bob_clicks_and_inferred_bits:
                if click_info['time_slot'] == alice_pn_info['time_slot']: 
                    bob_measurement_info_for_pn = click_info
                    break

            if bob_measurement_info_for_pn and bob_measurement_info_for_pn['bob_inferred_bit'] is not None:

                alice_intended_delta_phi = (alice_pn_info['modulated_phase'] - alice_pn_minus_1_info['modulated_phase']) % (2 * math.pi)

                if alice_intended_delta_phi > math.pi: alice_intended_delta_phi -= 2 * math.pi
                if alice_intended_delta_phi < -math.pi: alice_intended_delta_phi += 2 * math.pi

                alice_intended_bit = 0 if math.isclose(alice_intended_delta_phi, 0.0, abs_tol=1e-9) else 1
                
                alice_sifted_key.append(alice_intended_bit)
                bob_sifted_key.append(bob_measurement_info_for_pn['bob_inferred_bit'])
                sifted_time_slots.append(bob_measurement_info_for_pn['time_slot'])
                
        print(f"Sifting complete. Raw key length: {len(alice_sifted_key)}")

        self.shared_keys[target_node.node_id] = alice_sifted_key
        target_node.shared_keys[self.node_id] = bob_sifted_key 

    
        self.traffic_log.append({
            'type': 'key_generation',
            'partner': target_node.node_id,
            'initial_pulses': num_pulses,
            'sifted_length': len(alice_sifted_key),
        })
        
        return alice_sifted_key, bob_sifted_key

    def get_raw_sifted_key_with_neighbor(self, neighbor_id):
        """Retrieves the raw sifted key shared with a direct neighbor."""
        return self.shared_keys.get(neighbor_id)

    def relay_key_classically(self, sender_node_id, receiver_node_id, key_to_relay):

        key_with_sender = self.get_raw_sifted_key_with_neighbor(sender_node_id)
        key_with_receiver = self.get_raw_sifted_key_with_neighbor(receiver_node_id)

        if not key_with_sender:
            print(f"Error: Node {self.node_id} does not have a key with {sender_node_id} to relay.")
            return None
        if not key_with_receiver:
            print(f"Error: Node {self.node_id} does not have a key with {receiver_node_id} to relay.")
            return None
        print(f"Node {self.node_id} (relay) is holding the end-to-end key segment. Ready to extend to {receiver_node_id}.")
        return key_to_relay 


class Network:
    def __init__(self):
        self.nodes = {} 

    def add_node(self, node_id, **kwargs):
        """Adds a new node to the network."""
        if node_id in self.nodes:
            raise ValueError(f"Node {node_id} already exists.")
        self.nodes[node_id] = Node(node_id, **kwargs)
        return self.nodes[node_id]

    def connect_nodes(self, node1_id, node2_id, distance_km, attenuation_db_per_km=0.2):
        node1 = self.nodes.get(node1_id)
        node2 = self.nodes.get(node2_id)

        if not node1 or not node2:
            raise ValueError("Both nodes must exist in the network to create a connection.")

        channel = OpticalChannel(distance_km, attenuation_db_per_km)
        node1.add_link(node2_id, channel)
        node2.add_link(node1_id, channel) 
        print(f"Connected Node {node1_id} and Node {node2_id} with a {distance_km} km link.")

    def establish_end_to_end_raw_key(self, sender_id, receiver_id, path_nodes, num_pulses, pulse_repetition_rate_ns):
        if path_nodes[0] != sender_id or path_nodes[-1] != receiver_id:
            raise ValueError("Path must start with sender_id and end with receiver_id.")

        print(f"\n--- Establishing end-to-end RAW key from {sender_id} to {receiver_id} via path: {path_nodes} ---")
        
        
        current_end_to_end_key_segment = []
        
        for i in range(len(path_nodes) - 1):
            node1_id = path_nodes[i]
            node2_id = path_nodes[i+1]
            
            node1 = self.nodes[node1_id] 
            node2 = self.nodes[node2_id] 
            
            print(f"Attempting QKD link: {node1_id} <-> {node2_id}")
            
            
            alice_raw_sifted, bob_raw_sifted = node1.generate_and_share_key(
                node2, num_pulses, pulse_repetition_rate_ns
            )
            

            if i == 0: 
                current_end_to_end_key_segment = list(alice_raw_sifted) 
            
            else:
                current_end_to_end_key_segment.extend(alice_raw_sifted) 

            if not alice_raw_sifted:
                print(f"Failed to establish raw sifted key for link {node1_id}-{node2_id}. Aborting end-to-end key establishment.")
                return None
            print(f"Raw sifted key established for link {node1_id} and {node2_id} with length {len(alice_raw_sifted)}")

        print(f"End-to-end RAW sifted key established between {sender_id} and {receiver_id}.")
        return current_end_to_end_key_segment 
