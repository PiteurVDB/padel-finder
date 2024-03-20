import requests
from datetime import datetime, timedelta
import pandas as pd
import json
import os

with open('config.json', 'r') as file:
    config = json.load(file)

headers = {
  'Accept': 'application/json, text/plain, */*',
  'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
  'Connection': 'keep-alive',
  'Origin': 'https://arenapadel.doinsport.club',
  'Referer': 'https://arenapadel.doinsport.club/',
  'Sec-Fetch-Dest': 'empty',
  'Sec-Fetch-Mode': 'cors',
  'Sec-Fetch-Site': 'same-site',
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
  'X-Locale': 'fr',
  'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Windows"'
}

def get_plannings(date, start_hour, end_hour):

  url = f"https://api-v3.doinsport.club/clubs/playgrounds/plannings/{date}?club.id=5e956442-62fa-4f6f-9048-d51fbd7d42cf&from={start_hour}&to={end_hour}:00&activities.id=ce8c306e-224a-4f24-aa9d-6500580924dc&bookingType=unique"
  response = requests.request("GET", url, headers=headers)

  return response

def get_free_slots(end_date, start_hour, end_hour):

  slots_df = []
  start_date = datetime.strptime(datetime.today().date().strftime("%Y-%m-%d"), "%Y-%m-%d")
  nb_jour = (datetime.strptime(end_date, '%d/%m/%Y') - start_date).days

  for i in range(int(nb_jour)):
    date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
    print(f"Récupération des slots pour {date}")
    response = get_plannings(date, start_hour, end_hour)
    json_data = response.json()

    slots_data = []

    for field in json_data["hydra:member"]:
      if field["name"] != "Tournoi":
        slots_data.append(field)

    slots_jour_df = pd.json_normalize(slots_data, ["activities", "slots", "prices"], ["name", ["activities", "slots", "startAt"]])
    slots_jour_df["date"] = date
    slots_df.append(slots_jour_df)

  slots_df = pd.concat(slots_df)
  free_slots_df = slots_df[slots_df["bookable"] == True]
  free_slots_df["duration"] = free_slots_df["duration"] / 60
  free_slots_df["pricePerParticipant"] = free_slots_df["pricePerParticipant"] / 100
  free_slots_df = free_slots_df.rename(
    columns={'pricePerParticipant': 'price', 'name': 'terrain', 'activities.slots.startAt': 'start_hour'})
  free_slots_df = free_slots_df[["terrain", "date", "start_hour", "duration", "price"]]

  return free_slots_df

df = get_free_slots(config["end_date"], config["start_hour"], config["end_hour"])
new_row = {"terrain":"test", "date":"2024-03-20", "start_hour":"18:00", "duration":90, "price":6.5} # fake line
df.loc[len(df)] = new_row
print(df)

def compare_res(new_df):
  filename = f"padel_slots{config['end_date'].replace('/','-')}.csv"

  if os.path.exists(filename):
    old_df = pd.read_csv(filename)
    df_all = pd.merge(new_df, old_df, on=['terrain', 'date', 'start_hour', 'duration', 'price'],
                      how='outer', indicator=True)
    new_rows = df_all[df_all['_merge'] == 'left_only'].drop('_merge', axis=1)
    if not new_rows.empty:
      new_df.to_csv(filename, index=False)
    else :
      print("No new lines found.")
      return
  else:
    print(f"File '{filename}' does not exist.")
    new_df.to_csv(filename, index=False)

  return new_rows

new_rows = compare_res(df)