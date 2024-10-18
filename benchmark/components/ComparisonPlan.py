class ComparisonPlan():
    def __init__(self, trips, arrival_time):
        self.trips = trips
        self.arrival_time = arrival_time

    def print_plans(self):
        print(str(self))
        """
        if self.trips is not None:
            for trip in self.trips:
                trip.print_plan()
        else:
            print("No bus information entered for this plan")
        print(f"Arrival time: {self.arrival_time}")
        """

    def __str__(self):
        plan_str = ""
        if self.trips is not None:
            for trip in self.trips:
                plan_str += str(trip) + "\n"
        else:
            plan_str = "No bus information entered for this plan\n"
        plan_str += f"Arrival time: {self.arrival_time}"
        return plan_str