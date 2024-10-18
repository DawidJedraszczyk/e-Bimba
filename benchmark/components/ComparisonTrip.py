class ComparisonTrip():
    def __init__(self, start_time, end_time, start_location, end_location, bus):
        self.start_time = start_time
        self.end_time = end_time
        self.start_location = start_location
        self.end_location = end_location
        self.bus = bus

    def print_plan(self):
        print(f"\t\t{self.start_location}({self.start_time})---{self.bus}--->{self.end_location}({self.end_time})")

    def __str__(self):
        return f"{self.start_location}({self.start_time})---{self.bus}--->{self.end_location}({self.end_time})"