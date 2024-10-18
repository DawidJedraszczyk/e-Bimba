from benchmark.components.ComparisonPlan import ComparisonPlan
from benchmark.components.ComparisonTrip import ComparisonTrip
from benchmark.components.SampleRoute import SampleRoute

# All the routes here are for the timatable for 5.09.2024 - 30.09.2024
# Thursday = 2024-09-05
# Friday = 2024-09-06
# Saturday = 2024-09-07
# Sunday = 2024-09-08
# Monday = 2024-09-09
def get_custom_sample_routes():
    sample_routes = []
    #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="7:36:00", end_time="7:47:00", start_location="Poznań Główny", end_location="Politechnika", bus="5"))
    google_plan = ComparisonPlan(google_trips, arrival_time="7:53:00")

    jakdojade_trips.append(ComparisonTrip(start_time="7:36:00", end_time="7:50:00", start_location="Poznań Główny", end_location="Baraniaka", bus="5"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="7:57:00")

    sample_routes.append(SampleRoute(start_name="Poznań Główny", destination_name="Politechnika CW" , start_time= "7:30:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
                                      date='2024-09-05' ))

    #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="00:00:00", end_time="00:11:00", start_location="Most Dworcowy", end_location="Politechnika", bus="201"))
    google_plan = ComparisonPlan(google_trips, arrival_time="00:17:00")

    jakdojade_trips.append(ComparisonTrip(start_time="23:58:00", end_time="23:59:00", start_location="Poznań Główny", end_location="Rondo Kaponiera", bus="219"))
    jakdojade_trips.append(ComparisonTrip(start_time="00:02:00", end_time="00:11:00", start_location="Rondo Kaponiera", end_location="Politechnika", bus="201"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="00:17:00")

    sample_routes.append(SampleRoute(start_name="Poznań Główny", destination_name="Politechnika CW" , start_time= "23:45:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
                                      date='2024-09-05'))

    #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="00:00:00", end_time="00:11:00", start_location="Most Dworcowy", end_location="Politechnika", bus="201"))
    google_plan = ComparisonPlan(google_trips, arrival_time="00:17:00")

    jakdojade_trips.append(ComparisonTrip(start_time="23:58:00", end_time="23:59:00", start_location="Poznań Główny", end_location="Rondo Kaponiera", bus="219"))
    jakdojade_trips.append(ComparisonTrip(start_time="00:02:00", end_time="00:11:00", start_location="Rondo Kaponiera", end_location="Politechnika", bus="201"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="00:17:00")

    sample_routes.append(SampleRoute(start_name="Poznań Główny", destination_name="Politechnika CW" , start_time= "23:45:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
                                      date = '2024-09-07'))

    #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="7:39:00", end_time="7:54:00", start_location="Poznań Główny", end_location="Os. Lecha", bus="18"))
    google_plan = ComparisonPlan(google_trips, arrival_time="8:02:00")

    jakdojade_trips.append(ComparisonTrip(start_time="7:39:00", end_time="7:54:00", start_location="Poznań Główny", end_location="Os. Lecha", bus="18"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="8:02:00")

    sample_routes.append(SampleRoute(start_name="Poznań Główny", destination_name="Chartowo/Kurlandzka" , start_time= "7:30:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
                                      date='2024-09-05'))

    #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="0:04:00", end_time="0:18:00", start_location="Poznań Main Station", end_location="Kurlandzka", bus="222"))
    google_plan = ComparisonPlan(google_trips, arrival_time="0:21:00")

    jakdojade_trips.append(ComparisonTrip(start_time="0:04:00", end_time="0:18:00", start_location="Poznań Main Station", end_location="Kurlandzka", bus="222"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="0:21:00")

    sample_routes.append(SampleRoute(start_name="Poznań Główny", destination_name="Chartowo/Kurlandzka" , start_time= "23:45:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
                                      date='2024-09-05'))
    
    #########################
    # !!! na podstawie danego rozkładu, algorytm podaje autobus, który wedłóg jak dojadę nie istnieje
    # edit - jednak istnieje tylko w sobtonik rozkładzie jazdy
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="0:42:00", end_time="0:53:00", start_location="Stadion Miejski", end_location="Most Dworcowy", bus="214"))
    google_plan = ComparisonPlan(google_trips, arrival_time="0:57:00")

    jakdojade_trips.append(ComparisonTrip(start_time="0:43:00", end_time="0:54:00", start_location="Stadion Miejski", end_location="Rondo Kaponiera", bus="212"))
    jakdojade_trips.append(ComparisonTrip(start_time="1:00:00", end_time="1:02:00", start_location="Rondo Kaponiera", end_location="Poznań Główny", bus="215"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="1:02:00")

    sample_routes.append(SampleRoute(start_name="Stadion Lecha", destination_name="Poznań Główny" , start_time= "23:45:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
                                      date='2024-09-05'))

    #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="21:49:00", end_time="22:02:00", start_location="Stadion Miejski", end_location="Poznań Główny", bus="6"))
    google_plan = ComparisonPlan(google_trips, arrival_time="22:04:00")

    jakdojade_trips.append(ComparisonTrip(start_time="21:49:00", end_time="22:02:00", start_location="Stadion Miejski", end_location="Poznań Główny", bus="6"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="22:04:00")

    sample_routes.append(SampleRoute(start_name="Stadion Lecha", destination_name="Poznań Główny" , start_time= "21:37:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
                                      date='2024-09-05'))
    
    #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="10:04:00", end_time="10:12:00", start_location="Poznań Podolany ", end_location="Poznań Main", bus="Koleje wielkopolskie"))
    google_trips.append(ComparisonTrip(start_time="10:19:00", end_time="10:28:00", start_location="Dworzec Zachodni ", end_location="Serfitek", bus="12"))
    google_plan = ComparisonPlan(google_trips, arrival_time="10:41:00")

    jakdojade_trips.append(ComparisonTrip(start_time="9:59:00", end_time="10:18:00", start_location=" Strzeszyn Grecki", end_location="Most Teatralny", bus="164"))
    jakdojade_trips.append(ComparisonTrip(start_time="10:27:00", end_time="10:39:00", start_location="Most Teatralny", end_location="Politechnika", bus="3"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="10:46:00")

    sample_routes.append(SampleRoute(start_name="Strzeszyn - Owidiusza", destination_name="Politechnika CW" , start_time= "9:55:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
                                      date='2024-09-05'))
    
    #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="00:45:00", end_time="00:54:00", start_location="Politechnika", end_location="Rondo Kaponiera", bus="201"))
    google_trips.append(ComparisonTrip(start_time="01:00:00", end_time="01:30:00", start_location="Rondo Kaponiera", end_location="Strzeszyn Grecki", bus="216"))
    google_plan = ComparisonPlan(google_trips, arrival_time="01:33:00")

    jakdojade_trips.append(ComparisonTrip(start_time="00:45:00", end_time="00:54:00", start_location="Politechnika", end_location="Rondo Kaponiera", bus="201"))
    jakdojade_trips.append(ComparisonTrip(start_time="01:00:00", end_time="01:30:00", start_location="Rondo Kaponiera", end_location="Strzeszyn Grecki", bus="216"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="01:33:00")

    sample_routes.append(SampleRoute(start_name="Politechnika CW", destination_name="Strzeszyn - Owidiusza" , start_time= "23:59:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
                                      date='2024-09-05'))

 #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="00:23:00", end_time="00:30:00", start_location="Instytut Technologiczno-Przyrodniczy", end_location="Strzeszyn Grecki", bus="216"))
    google_plan = ComparisonPlan(google_trips, arrival_time="00:33:00")

    jakdojade_trips.append(ComparisonTrip(start_time="23:53:00", end_time="23:59:00", start_location="Stary Strzeszyn", end_location="Tułodzieckiej", bus="226"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="00:12:00")

    sample_routes.append(SampleRoute(start_name="Stary Strzeszyn", destination_name="Strzeszyn - Owidiusza" , start_time= "23:45:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
                                      date='2024-09-06'))

    #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="12:26:00", end_time="12:28:00", start_location="Strzeszyn Grecki", end_location="Puszkina", bus="170"))
    google_plan = ComparisonPlan(google_trips, arrival_time="12:48:00")

    jakdojade_trips.append(ComparisonTrip(start_time="12:46:00", end_time="12:54:00", start_location="Lubieńska", end_location=" Instytut Technol...zno-Przyrodniczy ", bus="160"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="13:02:00")

    sample_routes.append(SampleRoute(start_name="Strzeszyn - Owidiusza", destination_name="Stary Strzeszyn" , start_time= "12:20:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
                                      date='2024-09-05'))

    #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="12:20:00", end_time="13:13:00", start_location="Stary Strzeszyn", end_location="Smochowice - przejazd kolejowy", bus="Pieszo"))
    google_plan = ComparisonPlan(google_trips, arrival_time="13:13:00")

    jakdojade_trips.append(ComparisonTrip(start_time="12:20:00", end_time="13:13:00", start_location="Stary Strzeszyn", end_location="Smochowice - przejazd kolejowy", bus="Pieszo"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="13:13:00")

    sample_routes.append(SampleRoute(start_name="Stary Strzeszyn", destination_name="Smochowice - przejazd kolejowy" , start_time= "12:20:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
                                      date='2024-09-05'))

    #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="12:28:00", end_time="12:30:00", start_location="UAM Kampus", end_location="UAM Wydział Geografii", bus="198"))
    google_plan = ComparisonPlan(google_trips, arrival_time="12:42:00")

    jakdojade_trips.append(ComparisonTrip(start_time="12:28:00", end_time="12:30:00", start_location="UAM Kampus", end_location="UAM Wydział Geografii", bus="198"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="12:42:00")

    sample_routes.append(SampleRoute(start_name="Morasko - Kampus UAM", destination_name="Morasko - Bożydara" , start_time= "12:00:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
                                      date='2024-09-05'))

    #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="07:42:00", end_time="08:08:00", start_location="Błażeja", end_location="Poznań Główny", bus="10"))
    google_plan = ComparisonPlan(google_trips, arrival_time="08:10:00")

    jakdojade_trips.append(ComparisonTrip(start_time="07:42:00", end_time="08:08:00", start_location="Błażeja", end_location="Poznań Główny", bus="10"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="08:10:00")

    sample_routes.append(SampleRoute(start_name="Morasko - Bożydara", destination_name="Poznań Główny" , start_time= "7:30:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
                                     date='2024-09-05'))
    
    #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="12:45:00", end_time="12:56:00", start_location="Kiekrz dworzec", end_location="Poznań Główny", bus="REGIO"))
    google_trips.append(ComparisonTrip(start_time="13:11:00", end_time="13:32:00", start_location="Most Dworcowy", end_location="Szwedzka", bus="18"))
    google_plan = ComparisonPlan(google_trips, arrival_time="13:55:00")

    jakdojade_trips.append(ComparisonTrip(start_time="12:42:00", end_time="13:05:00", start_location="Kiekrz Kościół", end_location="Ogrody", bus="186"))
    jakdojade_trips.append(ComparisonTrip(start_time="13:13:00", end_time="13:47:00", start_location="Ogrody", end_location="Szwedzka", bus="18"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="13:55:00")

    sample_routes.append(SampleRoute(start_name="Kiekrz plaża parkowa", destination_name="IKEA" , start_time= "12:20:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
                                      date='2024-09-05'))
    
    #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="13:00:00", end_time="13:23:00", start_location="Kiekrz Kościół", end_location="Ogrody", bus="833"))
    google_trips.append(ComparisonTrip(start_time="13:31:00", end_time="13:51:00", start_location="Ogrody", end_location="Rondo Starołęka", bus="7"))
    google_trips.append(ComparisonTrip(start_time="13:57:00", end_time="14:01:00", start_location="Rondo Starołęka", end_location="Starołęka PKM", bus="13"))
    google_trips.append(ComparisonTrip(start_time="14:14:00", end_time="14:26:00", start_location="Starołęka PKM", end_location="Głuszyna", bus="158"))
    google_plan = ComparisonPlan(google_trips, arrival_time="14:30:00")

    jakdojade_trips.append(ComparisonTrip(start_time="12:47:00", end_time="13:19:00", start_location="Kiekrz Kościół", end_location="Ogrody", bus="837"))
    jakdojade_trips.append(ComparisonTrip(start_time="13:21:00", end_time="13:41:00", start_location="Ogrody", end_location=" Rondo Starołęka", bus="7"))
    jakdojade_trips.append(ComparisonTrip(start_time="13:45:00", end_time="13:49:00", start_location=" Rondo Starołęka", end_location="Rondo Żegrze ", bus="1"))
    jakdojade_trips.append(ComparisonTrip(start_time="13:51:00", end_time="13:53:00", start_location="Rondo Żegrze", end_location="Unii Lubelskiej", bus="3"))
    jakdojade_trips.append(ComparisonTrip(start_time="13:57:00", end_time="14:16:00", start_location="Unii Lubelskiej", end_location="Głuszyna", bus="153"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="14:19:00")

    sample_routes.append(SampleRoute(start_name="Kiekrz plaża parkowa", destination_name="Głuszyna" , start_time= "12:40:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan, 
                                     date='2024-09-05'))
    
    #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="14:11:00", end_time="14:24:00", start_location=" Port Lotniczy Ławica", end_location="Szpitalna", bus="159"))
    google_trips.append(ComparisonTrip(start_time="14:35:00", end_time="14:46:00", start_location="Ogrody", end_location="Smochowice", bus="821"))
    google_plan = ComparisonPlan(jakdojade_trips, arrival_time="15:04:00")

    jakdojade_trips.append(ComparisonTrip(start_time="14:11:00", end_time="14:22:00", start_location=" Port Lotniczy Ławica", end_location="Swoboda", bus="159"))
    jakdojade_trips.append(ComparisonTrip(start_time="14:27:00", end_time="14:32:00", start_location="Swoboda", end_location="Ogrody", bus="191"))
    jakdojade_trips.append(ComparisonTrip(start_time="14:35:00", end_time="14:46:00", start_location="Ogrody", end_location="Smochowice", bus="821"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="15:04:00")

    sample_routes.append(SampleRoute(start_name="Lotnisko", destination_name="Smochowice - przejazd kolejowy" , start_time= "14:00:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
                                      date="2024-09-09"))

    #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="14:21:00", end_time="14:31:00", start_location="Złotowska", end_location="Ogrody", bus="729"))
    google_trips.append(ComparisonTrip(start_time="14:46:00", end_time="14:57:00", start_location="Ogrody", end_location="Łupowska", bus="186"))
    google_plan = ComparisonPlan(jakdojade_trips, arrival_time="15:12:00")

    jakdojade_trips.append(ComparisonTrip(start_time="14:07:00", end_time="14:18:00", start_location=" Port Lotniczy Ławica", end_location="Swoboda", bus="159"))
    jakdojade_trips.append(ComparisonTrip(start_time="14:28:00", end_time="14:31:00", start_location="Swoboda", end_location="Ogrody", bus="729"))
    jakdojade_trips.append(ComparisonTrip(start_time="14:46:00", end_time="14:57:00", start_location="Ogrody", end_location="Łupowska", bus="186"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="15:12:00")

    sample_routes.append(SampleRoute(start_name="Lotnisko", destination_name="Smochowice - przejazd kolejowy" , start_time= "14:00:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
      date="2024-09-08"))
    
    #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="23:32:00", end_time="23:52:00", start_location="Port Lotniczy Ławica", end_location="Rondo Kaponiera", bus="159"))
    google_trips.append(ComparisonTrip(start_time="23:59:00", end_time="00:14:00", start_location="Rondo Kaponiera", end_location="Łupowska", bus="219"))
    google_plan = ComparisonPlan(jakdojade_trips, arrival_time="00:29:00")
    
    jakdojade_trips.append(ComparisonTrip(start_time="23:32:00", end_time="23:52:00", start_location="Port Lotniczy Ławica", end_location="Rondo Kaponiera", bus="159"))
    jakdojade_trips.append(ComparisonTrip(start_time="23:59:00", end_time="00:14:00", start_location="Rondo Kaponiera", end_location="Łupowska", bus="219"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="00:29:00")

    sample_routes.append(SampleRoute(start_name="Lotnisko", destination_name="Smochowice - przejazd kolejowy" , start_time= "23:20:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
      date="2024-09-08"))
    
    #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="00:24:00", end_time="00:35:00", start_location="Kołobrzeska", end_location="Most Teatralny", bus="219"))
    google_trips.append(ComparisonTrip(start_time="00:54:00", end_time="01:20:00", start_location=" Most Teatralny", end_location="Port Lotniczy Ławica ", bus="222"))
    google_plan = ComparisonPlan(google_trips, arrival_time="01:20:00")

    jakdojade_trips.append(ComparisonTrip(start_time="00:14:00", end_time="00:35:00", start_location="Łupowska", end_location="Most Teatralny", bus="219"))
    jakdojade_trips.append(ComparisonTrip(start_time="00:54:00", end_time="01:20:00", start_location=" Most Teatralny", end_location="Port Lotniczy Ławica ", bus="222"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="01:20:00")

    sample_routes.append(SampleRoute(start_name="Smochowice - przejazd kolejowy", destination_name="Lotnisko" , start_time= "23:20:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
      date="2024-09-08"))
    
    #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="00:24:00", end_time="00:35:00", start_location="Kołobrzeska", end_location="Most Teatralny", bus="219"))
    google_trips.append(ComparisonTrip(start_time="01:01:00", end_time="01:11:00", start_location="Most Teatralny", end_location="Rondo Rataje", bus="212"))
    google_trips.append(ComparisonTrip(start_time="01:20:00", end_time="01:35:00", start_location="Rondo Rataje", end_location="Głuszyna", bus="221"))
    google_plan = ComparisonPlan(google_trips, arrival_time="01:37:00")

    jakdojade_trips.append(ComparisonTrip(start_time="00:14:00", end_time="00:36:00", start_location="Łupowska", end_location="Rondo Kaponiera ", bus="219"))
    jakdojade_trips.append(ComparisonTrip(start_time="01:02:00", end_time="01:11:00", start_location="Rondo Kaponiera ", end_location="Politechnika", bus="201"))
    jakdojade_trips.append(ComparisonTrip(start_time="01:16:00", end_time="01:35:00", start_location="Politechnika", end_location="", bus="221"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="01:37:00")

    sample_routes.append(SampleRoute(start_name="Smochowice - przejazd kolejowy", destination_name="Głuszyna" , start_time= "23:20:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
      date="2024-09-08"))
    
    #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="11:32:00", end_time="11:51:00", start_location="Głuszyna", end_location="Unii Lubelskiej", bus="153"))
    google_trips.append(ComparisonTrip(start_time="12:00:00", end_time="12:24:00", start_location="Unii Lubelskiej", end_location="Most Teatralny", bus="3"))
    google_trips.append(ComparisonTrip(start_time="12:31:00", end_time="12:39:00", start_location="Most Teatralny", end_location="Ogrody", bus="2"))
    google_trips.append(ComparisonTrip(start_time="12:46:00", end_time="12:57:00", start_location="Ogrody", end_location="Łupowska", bus="156"))
    google_plan = ComparisonPlan(google_trips, arrival_time="13:11:00")

    jakdojade_trips.append(ComparisonTrip(start_time="11:44:00", end_time="11:56:00", start_location="Głuszyna", end_location="Starołęka PKM ", bus="158"))
    jakdojade_trips.append(ComparisonTrip(start_time="12:04::00", end_time="12:23:00", start_location="Starołęka PKM ", end_location=" Poznań Główny ", bus="12"))
    jakdojade_trips.append(ComparisonTrip(start_time="12:29:00", end_time="12:42:00", start_location="  Poznań Główny ", end_location="Ogrody", bus="18"))
    jakdojade_trips.append(ComparisonTrip(start_time="12:46:00", end_time="12:57:00", start_location="Ogrody", end_location="Łupowska", bus="156"))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="13:11:00")

    sample_routes.append(SampleRoute(start_name="Głuszyna", destination_name="Smochowice - przejazd kolejowy" , start_time= "11:20:00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
      date = '2024-09-07'))
    """
    #########################
    google_trips = []
    jakdojade_trips = []

    google_trips.append(ComparisonTrip(start_time="::00", end_time="::00", start_location="", end_location="", bus=""))
    google_plan = ComparisonPlan(google_trips, arrival_time="")

    jakdojade_trips.append(ComparisonTrip(start_time="::00", end_time="::00", start_location="", end_location="", bus=""))
    jakdojade_plan = ComparisonPlan(jakdojade_trips, arrival_time="::00")

    sample_routes.append(SampleRoute(start_name="", destination_name="" , start_time= "::00", jakdojade_plan=jakdojade_plan , google_plan=google_plan,
      week_day="Thursday"))
"""
    return sample_routes