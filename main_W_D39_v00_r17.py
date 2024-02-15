# r16_1: LowestPrice on Google Sheet gets Updated
# TODO: r17 Needs to ensure that IF and ONLY IF the price on the Google sheet is actually higher than the search price, THEN we replace it. but don't ALWAYS replace it.

# import necessary libraries:
import requests, os
from pprint import pprint
from datetime import datetime, timedelta

# import classes from other modules:
from data_manager_W_D39_v00_r17 import DataManager
from flight_search_W_D39_v00_r17 import FlightSearch
from notification_manager_W_D39_v00_r17 import NotificationManager

# initialize classes:
data_manager = DataManager()
flight_search = FlightSearch()
notification_manager = NotificationManager()

# fetch and print sheet data:
sheet_data = data_manager.get_request_for_getting_destination_data()
print("Fetched sheet data structure - before any updates:")
pprint(sheet_data)

# set origin iata code and sheety api details:
origin_iata_code = "SAN"
SHEETY_UPDATE_ENDPOINT = os.environ.get('SHEETY_UPDATE_ENDPOINT', 'Sheety Update Endpoint does not exist')
SHEETY_BEARER_TOKEN = os.environ.get('SHEETY_BEARER_TOKEN', 'Sheety Bearer Token does not exist')
headers = {"Authorization": f"Bearer {SHEETY_BEARER_TOKEN}", "Content-Type": "application/json"}

# update iata codes if missing:
for row in sheet_data:
    if not row.get("iataCode"):
        print(f"IataCode data is empty for {row['city']}, updating row:")
        iata_code = flight_search.get_destination_code(row["city"])
        row["iataCode"] = iata_code

# assuming update_destination_codes method exists to update the sheet:
data_manager.update_destination_codes(sheet_data)  # ensure this method is correctly implemented to update the Google Sheet

# set dates for flight search:
now = datetime.now()
tomorrow = now + timedelta(days=1)
six_months_from_today = now + timedelta(days=181)

# iterate through destinations to check for flights and update sheet if lower price is found:
for destination in sheet_data:
    city_name = destination.get('city')
    iata_code = destination.get('iataCode')
    sheet_lowest_price = float(destination.get('Lowest Price', float('inf')))  # use a high default value
    destination_id = destination.get('id')

    if iata_code:
        flight = flight_search.check_flights(origin_iata_code, iata_code, from_time=tomorrow, to_time=six_months_from_today)
        if flight:
            # verifying prices for additional layer of checking
            print(f"Verifying prices for {city_name}:")
            print(f"\tSheet's Lowest Price: ${sheet_lowest_price}")
            print(f"\tSirisFlightDeals Search Price: ${flight.price}")

            if flight.price < sheet_lowest_price:
                message = f"Low price alert! Only ${flight.price} to fly from {flight.origin_city}-{flight.origin_airport} to {flight.destination_city}-{flight.destination_airport}, from {flight.out_date} to {flight.return_date}."
                notification_manager.send_an_sms_text(message=message)

                updated_data = {"price": {"lowestPrice": flight.price}}
                response = requests.put(url=f"{SHEETY_UPDATE_ENDPOINT}/{destination_id}", json=updated_data, headers=headers)
                response.raise_for_status()  # check for successful request

                if response.status_code == 200:
                    print(f"Updated {city_name}'s lowest price in the sheet to: ${flight.price}")
                else:
                    print(f"Failed to update {city_name}'s lowest price. Status code: {response.status_code}")
            else:
                print(f"\tNo lower price found for {city_name} than the sheet price: ${sheet_lowest_price}.")
        else:
            print(f"\tNo flight results found for {city_name}.")
    else:
        print(f"Missing IATA code for {city_name}.")
