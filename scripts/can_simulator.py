#!/usr/bin/env python3
"""
NMEA2000 CAN Bus Simulator for PICAN HAT testing
This script simulates realistic NMEA2000 traffic from Garmin instruments
"""

import os
import time
import random
import can
from datetime import datetime
import struct
import math

def setup_can_interface():
    """Set up the CAN interface if not already configured"""
    try:
        # Set up interface without loopback for normal operation
        os.system('sudo ip link set can0 up type can bitrate 250000 loopback off')
        print("CAN interface configured successfully (loopback disabled)")
    except Exception as e:
        print(f"Error configuring CAN interface: {e}")
        return False
    return True

class DeviceSimulator:
    def __init__(self):
        # Initial values
        self.speed = 5.0  # knots
        self.depth = 25.0  # meters
        self.wind_speed = 8.0  # knots
        self.wind_angle = 45.0  # degrees
        self.latitude = 47.6062  # Seattle area
        self.longitude = -122.3321
        self.heading = 180.0  # degrees (will be converted to radians for NMEA2000)
        self.water_temp = 15.0  # Celsius (will be converted to Kelvin for NMEA2000)
        self.battery_voltage = 12.8  # Volts
        
        # Simulation state
        self.last_updates = {}  # Message timing
        self.simulation_start = time.time()
        
        # Long-term patterns
        self.wind_center = 45.0  # Wind tends to stay around this angle
        self.wind_center_shift = 0.0  # Gradual shift in prevailing wind
        self.battery_charging = False
        self.battery_cycle_time = 0
        self.last_battery_event = time.time()
        self.journey_start = time.time()
        self.planned_course = 180.0  # Overall intended heading
        
        # Device source addresses (based on typical Garmin network)
        self.sources = {
            'gps': 0x13,        # GPS/Chart Plotter
            'wind': 0x22,       # Wind sensor
            'depth': 0x32,      # Depth sounder
            'heading': 0x42,    # Compass/Heading sensor
            'battery': 0x52,    # Battery monitor
            'temp': 0x62,       # Temperature sensor
        }
        
    def update_simulated_values(self):
        """Update values with realistic patterns and relationships"""
        now = time.time()
        elapsed = now - self.simulation_start
        
        # Battery voltage simulation
        # Simulate charging cycles and gradual discharge
        if not self.battery_charging:
            # Discharging
            discharge_rate = 0.00005  # Volts per second (about 0.18V per hour)
            self.battery_voltage -= discharge_rate
            if self.battery_voltage <= 12.2:  # Low battery threshold
                self.battery_charging = True
                self.last_battery_event = now
        else:
            # Charging
            if now - self.last_battery_event < 3600:  # 1 hour charging cycle
                charge_rate = 0.0002  # Volts per second
                self.battery_voltage = min(13.8, self.battery_voltage + charge_rate)
            else:
                self.battery_charging = False
                self.last_battery_event = now
        
        # Wind patterns
        # Shift wind center gradually over time
        self.wind_center_shift += random.uniform(-0.01, 0.01)  # Very slow shift
        self.wind_center = (self.wind_center + self.wind_center_shift) % 360
        
        # Wind angle varies around the center with occasional gusts
        wind_variation = (
            math.sin(elapsed * 0.1) * 5 +  # Basic oscillation
            math.sin(elapsed * 0.027) * 10 +  # Longer period changes
            random.uniform(-2, 2)  # Random component
        )
        self.wind_angle = (self.wind_center + wind_variation) % 360
        
        # Wind speed with gusts and lulls
        base_wind = 8 + math.sin(elapsed * 0.05) * 3  # Base wind pattern
        gust = max(0, math.sin(elapsed * 0.7) * 5)  # Occasional gusts
        self.wind_speed = max(0, base_wind + gust + random.uniform(-0.5, 0.5))
        
        # Heading variations (small corrections + wave influence)
        heading_error = math.sin(elapsed * 0.2) * 2  # Basic wave influence
        correction = (self.planned_course - self.heading) * 0.1  # Gradual correction
        self.heading = (self.heading + heading_error + correction + random.uniform(-0.5, 0.5)) % 360
        
        # Speed variations based on wind and waves
        wind_factor = math.cos(math.radians(self.wind_angle - self.heading)) * 0.2
        wave_factor = math.sin(elapsed * 0.3) * 0.5
        self.speed = max(0, self.speed + wind_factor + wave_factor + random.uniform(-0.1, 0.1))
        self.speed = min(12, max(0, self.speed))  # Limit to realistic range
        
        # Depth variations (simulate seabed contours)
        depth_pattern = (
            math.sin(elapsed * 0.01) * 10 +  # Long period changes
            math.sin(elapsed * 0.1) * 2    # Shorter variations
        )
        self.depth = max(3, 25 + depth_pattern + random.uniform(-0.2, 0.2))
        
        # Water temperature (very gradual changes)
        # Temperature varies between 50-70°F (10-21°C)
        temp_variation = math.sin(elapsed * 0.001) * 5  # Daily variation
        self.water_temp = 15.5 + temp_variation + random.uniform(-0.05, 0.05)  # Base temp ~60°F
        
        # Update position based on speed and heading
        speed_ms = self.speed * 0.514444  # Convert knots to m/s
        lat_change = math.cos(math.radians(self.heading)) * speed_ms * 0.0000089
        lon_change = math.sin(math.radians(self.heading)) * speed_ms * 0.0000089
        self.latitude += lat_change
        self.longitude += lon_change

    def should_send(self, pgn, frequency):
        """Determine if we should send a message based on its frequency"""
        now = time.time()
        if pgn not in self.last_updates:
            self.last_updates[pgn] = 0
        if now - self.last_updates[pgn] >= (1.0 / frequency):
            self.last_updates[pgn] = now
            return True
        return False

    def generate_nmea2000_messages(self):
        """Generate NMEA2000 messages with realistic timing and data"""
        messages = []
        
        # Update simulated values
        self.update_simulated_values()
        
        # System Time (PGN 126992) - 1Hz
        if self.should_send(126992, 1):
            now = datetime.utcnow()
            messages.append({
                'pgn': 0x1F010,
                'source': self.sources['gps'],
                'data': [0x00, 0xFF, now.second, now.minute, now.hour, 
                        now.day, now.month, now.year - 2000]
            })
        
        # Vessel Heading (PGN 127250) - 10Hz
        if self.should_send(127250, 10):
            # Units: Radians * 10000
            heading_rad = math.radians(self.heading)
            heading_bytes = list(struct.pack('<H', int(heading_rad * 10000)))
            messages.append({
                'pgn': 0x1F112,
                'source': self.sources['heading'],
                'data': [0x00] + heading_bytes + [0xFF] * 5
            })
        
        # Speed through water (PGN 128259) - 1Hz
        if self.should_send(128259, 1):
            # Units: 0.01 m/s
            speed_ms = self.speed * 0.514444  # Convert knots to m/s
            speed_bytes = list(struct.pack('<H', int(speed_ms * 100)))
            messages.append({
                'pgn': 0x1F503,
                'source': self.sources['depth'],  # Usually combined with depth sensor
                'data': [0x00] + speed_bytes + [0xFF] * 5
            })
        
        # Water depth (PGN 128267) - 2Hz
        if self.should_send(128267, 2):
            # Units: 0.01 meters
            depth_bytes = list(struct.pack('<H', int(self.depth * 100)))
            messages.append({
                'pgn': 0x1F50B,
                'source': self.sources['depth'],
                'data': [0x00] + depth_bytes + [0xFF] * 5
            })
        
        # GPS Position (PGN 129029) - 1Hz
        if self.should_send(129029, 1):
            # Units: 1e-7 degrees
            lat_bytes = list(struct.pack('<q', int(self.latitude * 1e7)))[:4]
            lon_bytes = list(struct.pack('<q', int(self.longitude * 1e7)))[:4]
            messages.append({
                'pgn': 0x1F805,
                'source': self.sources['gps'],
                'data': lat_bytes + lon_bytes
            })
        
        # Wind data (PGN 130306) - 10Hz
        if self.should_send(130306, 10):
            # Speed units: 0.01 m/s
            # Angle units: 0.0001 radians
            wind_speed_ms = self.wind_speed * 0.514444  # Convert knots to m/s
            wind_angle_rad = math.radians(self.wind_angle)
            speed_bytes = list(struct.pack('<H', int(wind_speed_ms * 100)))
            angle_bytes = list(struct.pack('<H', int(wind_angle_rad * 10000)))
            messages.append({
                'pgn': 0x1FD02,
                'source': self.sources['wind'],
                'data': [0x00] + speed_bytes + angle_bytes + [0xFF] * 3
            })
        
        # Water Temperature (PGN 130310) - 0.5Hz
        if self.should_send(130310, 0.5):
            # Convert Celsius to Kelvin (NMEA2000 requires Kelvin)
            # Note: SignalK will convert to F/C based on user preference
            temp_k = self.water_temp + 273.15  # Convert to Kelvin
            temp_bytes = list(struct.pack('<H', int(temp_k * 100)))  # Units: 0.01 Kelvin
            messages.append({
                'pgn': 0x1FD06,
                'source': self.sources['temp'],
                'data': [0x00] + temp_bytes + [0xFF] * 5
            })
        
        # Battery Status (PGN 127508) - 0.5Hz
        if self.should_send(127508, 0.5):
            # Units: 0.01 Volts
            voltage_bytes = list(struct.pack('<H', int(self.battery_voltage * 100)))
            messages.append({
                'pgn': 0x1F214,
                'source': self.sources['battery'],
                'data': [0x00] + voltage_bytes + [0xFF] * 5
            })
            
        return messages

def main():
    """Main function to simulate NMEA2000 traffic"""
    print("Starting NMEA2000 CAN bus simulator (Garmin instruments)...")
    
    if not setup_can_interface():
        return
    
    try:
        bus = can.interface.Bus(channel='can0', bustype='socketcan')
        print("Successfully connected to CAN bus")
        
        simulator = DeviceSimulator()
        
        while True:
            messages = simulator.generate_nmea2000_messages()
            
            for msg_data in messages:
                # Construct 29-bit CAN ID:
                # - Priority (3 bits, default 2)
                # - PGN (16 bits)
                # - Source address (8 bits)
                priority = 2
                pgn = msg_data['pgn']
                source = msg_data['source']
                can_id = (priority << 26) | (pgn << 8) | source
                
                message = can.Message(
                    arbitration_id=can_id,
                    data=msg_data['data'],
                    is_extended_id=True
                )
                
                try:
                    bus.send(message)
                    print(f"Sent message - PGN: {hex(msg_data['pgn'])} from source: {hex(source)}")
                except can.CanError:
                    print("Message NOT sent")
            
            # No artificial rate limiting - let messages flow at their natural device frequencies
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("\nShutting down CAN simulator...")
        try:
            bus.shutdown()
        except:
            pass

if __name__ == "__main__":
    main()
