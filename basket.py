import time
import os
from collections import deque
from typing import List, Dict, Tuple

# --- Constants for console colors and drawing ---
# ANSI escape codes for colors
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RED = "\033[91m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"

# Drawing characters
ENTRY_CHAR = "🔽"
STATION_CHAR = "🏭"
WAITING_CHAR = "⏰"
BASKET_CHAR = "📦"
EMPTY_CHAR = "  "
ARROW_RIGHT = "───▶"
ARROW_LEFT = "◀───"
VERTICAL_LINE = "  │"
HORIZONTAL_LINE = "──"
LIFT_CHAR = "⬇️"

# --- 1. Class Basket: ตะกร้า ---
class Basket:
    def __init__(self, id: int, route: List[str]):
        self.id = id
        self.route = route[:] # Use a copy of the route
        self.next_station_index = 0
        self.location = "Entry Point"
        self.completed_stations = []
        self.start_time = time.time()
        self.finish_time = None

    @property
    def next_station(self) -> str:
        return self.route[self.next_station_index] if self.next_station_index < len(self.route) else None

    def update_route(self):
        """อัพเดทสถานีถัดไปหลังจากทำสถานีปัจจุบันเสร็จแล้ว"""
        if self.next_station_index < len(self.route):
            self.completed_stations.append(self.route[self.next_station_index])
            self.next_station_index += 1
            
    def __repr__(self):
        next_station_info = self.next_station if self.next_station else "Finish"
        return f"{BASKET_CHAR}{self.id:02d} ({next_station_info})"

# --- 2. Class Station: สถานีจัดยา ---
class Station:
    def __init__(self, name: str, processing_time: float = 1.0):
        self.name = name
        self.current_basket: Basket = None
        self.is_available = True
        self.processing_time = processing_time
        self.finish_time = 0.0

    def load_basket(self, basket: Basket):
        if not self.is_available:
            raise Exception(f"Station {self.name} is not available!")

        self.current_basket = basket
        self.is_available = False
        basket.location = f"In_Station_{self.name}"
        self.finish_time = time.time() + self.processing_time

    def finish_processing(self) -> Basket:
        if self.current_basket and time.time() >= self.finish_time:
            released_basket = self.current_basket
            released_basket.update_route()
            self.current_basket = None
            self.is_available = True
            released_basket.location = f"Out_of_Station_{self.name}"
            return released_basket
        return None

    def __repr__(self):
        status = "Available" if self.is_available else f"Busy (Basket {self.current_basket.id})"
        return f"Station({self.name}, Status: {status})"

# --- 3. Class WaitingZone: จุดพักรอ ---
class WaitingZone:
    def __init__(self, name: str, capacity: int = 1):
        self.name = name
        self.queue: deque[Basket] = deque()
        self.capacity = capacity

    def add_basket(self, basket: Basket) -> bool:
        if len(self.queue) < self.capacity:
            self.queue.append(basket)
            basket.location = self.name
            return True
        return False

    def get_next_basket(self) -> Basket:
        if self.queue:
            return self.queue.popleft()
        return None
    
    def is_full(self) -> bool:
        return len(self.queue) >= self.capacity

    def __repr__(self):
        return f"WaitingZone({self.name}, Queued: {len(self.queue)}/{self.capacity})"


# --- 4. Class ConveyorSystem: ระบบสายพานหลัก ---
class ConveyorSystem:
    def __init__(self, station_details: Dict[str, float], waiting_capacity: int = 1):
        self.station_names = list(station_details.keys()) # Keep order for drawing
        self.stations: Dict[str, Station] = {
            name: Station(name, time) 
            for name, time in station_details.items()
        }
        self.waiting_zones: Dict[str, WaitingZone] = {
            f"Waiting_{name}": WaitingZone(f"Waiting_{name}", waiting_capacity)
            for name in station_details.keys()
        }
        self.entry_queue: deque[Basket] = deque()
        self.active_baskets: List[Basket] = [] # All baskets in the system (including entry_queue and finished ones)
        self.finished_baskets: List[Basket] = [] # Baskets that have completed all their routes
        self.log: List[str] = []
        self.is_entry_halted = False

    def initialize_baskets(self, baskets_data: List[Tuple[int, List[str]]]):
        for id, route in baskets_data:
            basket = Basket(id, route)
            self.entry_queue.append(basket)
            self.active_baskets.append(basket) # Add to active_baskets to track start_time for all
        self.log.append(f"--- System Initialized with {len(self.active_baskets)} Baskets ---")

    def detect_and_manage_collision(self, basket: Basket) -> str:
        target_station_name = basket.next_station
        
        if not target_station_name:
            # Basket has completed all its routes
            basket.finish_time = time.time()
            self.log.append(f"{GREEN}[DONE] Basket {basket.id} FINISHED process.{RESET}")
            # Remove from active_baskets and move to finished_baskets
            if basket in self.active_baskets: # Check if it's still in active_baskets
                self.active_baskets.remove(basket) 
            self.finished_baskets.append(basket)
            return "Finished"

        target_station = self.stations.get(target_station_name)
        waiting_zone = self.waiting_zones.get(f"Waiting_{target_station_name}")

        if not target_station or not waiting_zone:
            self.log.append(f"{RED}[ERROR] Basket {basket.id} cannot find station {target_station_name}{RESET}")
            return "Error"

        if target_station.is_available:
            target_station.load_basket(basket)
            self.log.append(f"{BLUE}[MOVE] Basket {basket.id} moved to Station {target_station_name}.{RESET}")
            self.is_entry_halted = False 
            return "Loaded"
        else:
            if not waiting_zone.is_full():
                waiting_zone.add_basket(basket)
                self.log.append(f"{YELLOW}[WAIT] Basket {basket.id} cannot enter {target_station_name}. Moved to {waiting_zone.name}.{RESET}")
                self.is_entry_halted = False 
                return "Waiting"
            else:
                self.is_entry_halted = True 
                self.log.append(f"{RED}[HALT] Basket {basket.id} cannot enter {target_station_name}. {waiting_zone.name} is full. Entry Halted!{RESET}")
                return "Halted"

    def simulate_tick(self):
        # 1. Release basket from Entry Point if possible
        if self.entry_queue and not self.is_entry_halted:
            released_basket_from_entry = self.entry_queue.popleft()
            self.log.append(f"{CYAN}[ENTRY] Basket {released_basket_from_entry.id} released from Entry Point.{RESET}")
            self.detect_and_manage_collision(released_basket_from_entry) 

        # 2. Process stations: release finished baskets and load waiting ones
        released_baskets_from_station: List[Basket] = [] 
        for station_name in self.station_names: # Iterate in order for consistent processing
            station = self.stations[station_name]
            basket_finished = station.finish_processing()
            if basket_finished:
                self.log.append(f"{MAGENTA}[SIGNAL] Station {station_name} finished Basket {basket_finished.id}.{RESET}")
                released_baskets_from_station.append(basket_finished)
                
                # If station becomes available, load next from waiting zone
                waiting_zone = self.waiting_zones[f"Waiting_{station_name}"]
                next_in_queue = waiting_zone.get_next_basket()
                if next_in_queue:
                    station.load_basket(next_in_queue)
                    self.log.append(f"{BLUE}[MOVE] Basket {next_in_queue.id} from {waiting_zone.name} to Station {station_name}.{RESET}")
                    
        # 3. Process movement of baskets released from stations
        for basket in released_baskets_from_station:
            self.detect_and_manage_collision(basket)

    def clear_console(self):
        """Clears the terminal console."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def draw_system_state(self, tick: int):
        """
        Draws the current state of the conveyor system to the console
        with animation-like updates.
        """
        self.clear_console()
        
        # --- Draw the main layout ---
        print(f"{BOLD}⚙️ CONVEYOR SYSTEM SIMULATION - TICK {tick} ⚙️{RESET}")
        print("="*80)

        # Entry Point
        entry_queue_str = " | ".join([f"{b.id}" for b in self.entry_queue])
        entry_status = "⏸️ HALTED" if self.is_entry_halted else "▶️ ACTIVE"
        print(f" {BOLD}ENTRY POINT{RESET} ({entry_status}): [{entry_queue_str}]")
        print(f"       {ENTRY_CHAR}")
        
        # Main Track - showing any basket "on track" (not in station/waiting)
        main_track_baskets = []
        # Find baskets that are "Out_of_Station_X" and will move to next
        for b in self.active_baskets:
            if b.location.startswith("Out_of_Station_") and b.next_station:
                main_track_baskets.append(f"{BASKET_CHAR}{b.id}")
            elif b.location == "Entry Point": # Baskets newly released but haven't found a spot yet
                 main_track_baskets.append(f"{BASKET_CHAR}{b.id}")
        
        main_track_str = " ".join(main_track_baskets)
        print(f" {BOLD}MAIN TRACK{RESET}: {main_track_str}")
        print(" " + "┌" + HORIZONTAL_LINE*10 + "┐")
        print(" │" + " "*40 + "│")
        
        # Stations and Waiting Zones
        station_line = " "
        waiting_line = " "
        station_name_line = " "
        
        for i, name in enumerate(self.station_names):
            station = self.stations[name]
            waiting_zone = self.waiting_zones[f"Waiting_{name}"]

            # Station
            station_status_color = RED if not station.is_available else GREEN
            basket_in_station = f"{BASKET_CHAR}{station.current_basket.id:02d}" if station.current_basket else EMPTY_CHAR
            
            station_line += f"{station_status_color}{STATION_CHAR} {basket_in_station} {RESET}" 
            station_name_line += f" {name}{RESET}      " # Align with basket_in_station

            # Waiting Zone
            waiting_status_color = YELLOW if waiting_zone.queue else GREEN
            waiting_basket_str = " ".join([f"{BASKET_CHAR}{b.id:02d}" for b in waiting_zone.queue])
            if not waiting_basket_str: waiting_basket_str = EMPTY_CHAR

            waiting_line += f"{waiting_status_color}{WAITING_CHAR} {waiting_basket_str} {RESET}"
            
            if i < len(self.station_names) - 1:
                station_line += ARROW_RIGHT
                waiting_line += " "*len(ARROW_RIGHT)
                station_name_line += "     "
            else:
                station_line += f" {LIFT_CHAR} LIFT"

        print(station_name_line)
        print(station_line)
        print(" "*3 + VERTICAL_LINE*2 + " "*(len(ARROW_RIGHT)-1) + VERTICAL_LINE*2 + " "*(len(ARROW_RIGHT)-1) + VERTICAL_LINE*2)
        print(waiting_line)
        
        print("\n" + "="*80)
        
        # Display Log
        print(f"\n{BOLD}📝 LOG:{RESET}")
        for entry in self.log:
            print(f"  > {entry}")
        
        # Display detailed status (non-animated part)
        print(f"\n{BOLD}📊 DETAILED STATUS:{RESET}")
        for name, station in self.stations.items():
            basket_info = f"Basket {station.current_basket.id}" if station.current_basket else "N/A"
            status = "🟢 Available" if station.is_available else f"🔴 Busy ({basket_info})"
            print(f"- {station.name}: {status}")
        
        for name, zone in self.waiting_zones.items():
            queue_list = ", ".join([str(b.id) for b in zone.queue])
            status = "FULL" if zone.is_full() else "Free"
            print(f"- {zone.name}: {len(zone.queue)}/{zone.capacity} ({status}). Queue: [{queue_list}]")

        active_basket_details = ", ".join([f"B{b.id}({b.next_station or 'Fin'})" for b in self.active_baskets])
        print(f"- Active Baskets: [{active_basket_details}]")
        print(f"- Entry Halted: {self.is_entry_halted}")

        print("="*80)


    def run_simulation(self, total_ticks: int = 20, tick_interval: float = 1.0):
        print(f"{BOLD}{GREEN}--- STARTING SIMULATION for {total_ticks} ticks ---{RESET}")
        input(f"{BOLD}Press Enter to start simulation...{RESET}")

        for tick in range(1, total_ticks + 1):
            if not self.active_baskets and not self.entry_queue:
                self.draw_system_state(tick) # Draw final state
                print(f"\n{GREEN}🎉 All baskets finished! Stopping simulation. 🎉{RESET}")
                break
            
            self.log = [] # Clear log for the current tick
            self.simulate_tick()
            self.draw_system_state(tick)
            
            time.sleep(tick_interval)
            
        self.calculate_average_time()


    def calculate_average_time(self):
        """Calculates and prints average time for finished baskets."""
        if not self.finished_baskets:
             return 

        total_time = 0
        print(f"\n\n{BOLD}--- 📊 SUMMARY (Hard Level) 📊 ---{RESET}")
        for basket in self.finished_baskets:
            time_taken = basket.finish_time - basket.start_time
            total_time += time_taken
            print(f"- Basket {basket.id}: Time taken = {time_taken:.2f} seconds.")

        avg_time = total_time / len(self.finished_baskets)
        print(f"**- Average Time per Basket: {avg_time:.2f} seconds.**")
        print(f"{BOLD}-----------------------------------{RESET}")


# --- ตัวอย่างการเรียกใช้ระบบ ---
if __name__ == "__main__":
    # 1. รับข้อมูลจำนวนตะกร้า และลำดับสถานีของแต่ละตะกร้า
    baskets_input = [
        # (ID, [Route])
        (1, ['A', 'B']),
        (2, ['A', 'C']),
        (3, ['B', 'C', 'A']), # ตัวอย่างกรณีพิเศษ
        (4, ['A']),
        (5, ['C', 'B']),
        (6, ['A', 'B', 'C']),
    ]
    
    # เงื่อนไขเสริม: แต่ละสถานีมีระยะเวลา “จัดยา” ต่างกัน (ชื่อสถานี: เวลาจัดยา)
    station_times = {
        'A': 2.0, # นายเอจัดยาปานกลาง
        'B': 3.0, # นายบีจัดยาช้า
        'C': 1.5  # นายซีค่อนข้างเร็ว
    }

    # สร้างระบบ
    system = ConveyorSystem(
        station_details=station_times,
        waiting_capacity=1 # จุดพักรอแต่ละจุดรับได้แค่ 1 ใบ
    )

    # ใส่ตะกร้าเข้าระบบ
    system.initialize_baskets(baskets_input)

    # รันการจำลอง (30 รอบ, หน่วงเวลา 1 วินาทีต่อรอบ)
    # ปรับ total_ticks และ tick_interval เพื่อดูการทำงานที่ต่างกันได้
    system.run_simulation(total_ticks=30, tick_interval=1.0)