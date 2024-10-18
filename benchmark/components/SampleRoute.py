from datetime import datetime
from benchmark.routes_generating.resources import locations_dict

class SampleRoute:
    def __init__(self,
                start_name,
                destination_name,
                start_time,
                jakdojade_plan = None,
                google_plan = None,
                date = "2024-09-05"
                ):
        
        self.start_cords = locations_dict[start_name]
        self.start_name = start_name
        self.destination_cords = locations_dict[destination_name]
        self.destination_name = destination_name
        self.start_time = start_time
        self.jakdojade_plan = jakdojade_plan
        self.google_plan = google_plan
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        self.week_day = date_obj.strftime('%A')
        self.date = date

    def print_comparison_plans(self):
        if self.google_plan is not None:
            print("\t*****************************")
            print("\tGoogle plan:")
            self.google_plan.print_plans()
        if self.jakdojade_plan is not None:
            print("\t*****************************")
            print("\tJakdojade plan:")
            self.jakdojade_plan.print_plans()