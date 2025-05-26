from Network import Network

import math 

def calculate_qber(alice_sifted_key, bob_sifted_key):

    if len(alice_sifted_key) != len(bob_sifted_key):
        raise ValueError("Sifted keys must be of the same length to calculate QBER.")

    if not alice_sifted_key: 
        return 0.0, 0

    num_errors = 0
    for i in range(len(alice_sifted_key)):
        if alice_sifted_key[i] != bob_sifted_key[i]:
            num_errors += 1
    
    qber = num_errors / len(alice_sifted_key)
    return qber, num_errors

def run_point_to_point_simulation(num_pulses_per_link=10000, distance_km=20, mu=0.2,
                                  detector_efficiency=0.9, dark_count_rate_per_ns=1e-7,
                                  pulse_repetition_rate_ns=1):

    print("\n--- Running Point-to-Point QKD Simulation ---")
    

    temp_network = Network()
    node_alice = temp_network.add_node('Alice', avg_photon_number=mu)
    node_bob = temp_network.add_node('Bob', detector_efficiency=detector_efficiency,
                                        dark_count_rate=dark_count_rate_per_ns)
    temp_network.connect_nodes('Alice', 'Bob', distance_km=distance_km)
    
    print(f"Simulating point-to-point QKD for {distance_km} km with {num_pulses_per_link} pulses.")
    

    alice_raw_sifted_key, bob_raw_sifted_key = node_alice.generate_and_share_key(
        node_bob, num_pulses_per_link, pulse_repetition_rate_ns
    )
    

    qber, num_errors = calculate_qber(alice_raw_sifted_key, bob_raw_sifted_key)

    print(f"\n--- Point-to-Point Results ({distance_km} km) ---")
    print(f"Initial Pulses Sent: {num_pulses_per_link}")
    print(f"Raw Sifted Key Length: {len(alice_raw_sifted_key)}")
    print(f"Raw QBER: {qber:.4f} ({num_errors} errors)")
    

    if num_pulses_per_link > 0:
        raw_key_rate_per_pulse = len(alice_raw_sifted_key) / num_pulses_per_link
        print(f"Raw Sifted Key Rate (bits/pulse): {raw_key_rate_per_pulse:.4f}")
    

    total_time_s = (num_pulses_per_link * pulse_repetition_rate_ns) / 1e9
    if total_time_s > 0:
        raw_key_rate_bps = len(alice_raw_sifted_key) / total_time_s
        print(f"Raw Sifted Key Rate (bits/second): {raw_key_rate_bps:.2f} bps")
    else:
        print("Raw Sifted Key Rate (bits/second): N/A (too few pulses)")
        
    return len(alice_raw_sifted_key), qber

def run_multi_node_trusted_relay_simulation(num_pulses_per_link=10000, link_distance_km=10, num_relays=1,
                                            mu=0.2, detector_efficiency=0.9, dark_count_rate_per_ns=1e-7,
                                            pulse_repetition_rate_ns=1):
    print(f"\n--- Running Multi-Node (Trusted Relay) QKD Simulation with {num_relays} relay(s) ---")
    
    network = Network()
    

    sender_id = 'Alice'
    receiver_id = 'Bob'
    relay_ids = [f'Relay{i+1}' for i in range(num_relays)]
    all_node_ids = [sender_id] + relay_ids + [receiver_id]

    for node_id in all_node_ids:
        network.add_node(node_id, avg_photon_number=mu,
                         detector_efficiency=detector_efficiency, dark_count_rate=dark_count_rate_per_ns)
 
    for i in range(len(all_node_ids) - 1):
        node1_id = all_node_ids[i]
        node2_id = all_node_ids[i+1]
        network.connect_nodes(node1_id, node2_id, distance_km=link_distance_km)

    path = all_node_ids
    

    final_end_to_end_raw_key = network.establish_end_to_end_raw_key(
        sender_id, receiver_id, path, num_pulses_per_link, pulse_repetition_rate_ns
    )

    print(f"\n--- Multi-Node Results ({num_relays} relays, {link_distance_km}km per link) ---")
    if final_end_to_end_raw_key is not None:
        print(f"End-to-End Raw Sifted Key Length: {len(final_end_to_end_raw_key)}")
        
        num_links = len(all_node_ids) - 1
        total_distance_km = num_links * link_distance_km
        total_pulses_generated_across_all_links = num_pulses_per_link * num_links 
        
        print(f"Total Network Distance: {total_distance_km} km")
        print(f"Total Pulses Generated (sum across links): {total_pulses_generated_across_all_links}")
        
        total_time_s = (total_pulses_generated_across_all_links * pulse_repetition_rate_ns) / 1e9
        
        if total_time_s > 0:
            end_to_end_raw_key_rate_bps = len(final_end_to_end_raw_key) / total_time_s
            print(f"End-to-End Raw Sifted Key Rate (bits/second): {end_to_end_raw_key_rate_bps:.2f} bps")
        else:
            print("End-to-End Raw Sifted Key Rate (bits/second): N/A (too few pulses)")
    else:
        print("End-to-End raw sifted key establishment failed.")
        
    return final_end_to_end_raw_key


if __name__ == "__main__":
   
    common_params = {
        'num_pulses_per_link': 5000, 
        'mu': 0.2,          
        'detector_efficiency': 0.9,
        'dark_count_rate_per_ns': 1e-9, 
        'pulse_repetition_rate_ns': 1    
    }

  
    print("\n" + "="*70)
    print("        RUNNING POINT-TO-POINT QKD SIMULATION")
    print("="*70)
    final_key_len_ptp, qber_ptp = run_point_to_point_simulation(
        distance_km=20, 
        **common_params
    )

    print("\n" + "="*70)
    print("        RUNNING MULTI-NODE (1 RELAY) QKD SIMULATION")
    print("="*70)
    final_key_multi_node_1_relay = run_multi_node_trusted_relay_simulation(
        link_distance_km=20, 
        num_relays=1,      
        **common_params
    )

 
    print("\n" + "="*70)
    print("        RUNNING MULTI-NODE (2 RELAYS) QKD SIMULATION")
    print("="*70)
    final_key_multi_node_2_relays = run_multi_node_trusted_relay_simulation(
        link_distance_km=20, 
        num_relays=2,      
        **common_params
    )
    
    print("\n" + "="*70)
    print("SIMULATIONS COMPLETE!")
    print("="*70)
