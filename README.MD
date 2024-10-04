# 🚒 MissionChief Bot
This is a MissionChief bot that automates the process of logging into your account and completing your missions using the Chromium driver.

# CURRENTLY ONLY WORKS ON NA

## 🚨 Dispatching
1. Dispatch vehicles to missions
2. Dispatch certain vehicles based off of personnel
3. Transport Prisoners to one of your jails automatically
4. Transport Patients from missions to one of your hospitals automatically
5. If units are already on scene it’ll just dispatch the units that are missing
6. Automatically Dispatches EMS Chief if patients > or = 10
7. Automatically dispatches Wrecker or Flatbed Carrier based on Crashed cars in a mission
8. Automatically dispatches a Prisoner Transport Van if the amount of prisoners is greater than 1
9. Leave patient at scene if no transport locations are available

## 🎯 Missions
1. Ignores Missions in-progress (yellow or green)
2. Grabs mission data of missing vehicles
3. Grabs only missing personnel


## 📋 Prerequisites
Before running the bot, make sure you have the following installed:

`Python 3.x`

## 🛠️ Installation
1. Clone this repository or download the code.
2. Install the required Python dependencies by running pip install -r requirements.txt in the project directory.
3. Update the config.ini
4. Enjoy!


## ⚙️ Configuration
#### Modify the config.ini file in the project directory and fill in the following:

```ini
[credentials]
username = your_username
password = your_password

[client]
server = us
headless = true
```

Replace your_username and your_password with your actual MissionChief credentials.

## 🚀 Usage
1. Open a terminal or command prompt and navigate to the project directory.
2. Run the bot by executing python main.py.
3. The bot will log into your MissionChief account and start completing your missions.
4. In order to update your list of vehicles, run python clean.py

## 📸 Bot in Action:
![img.png](/imgs/img.png)
![img_1.png](/imgs/img_1.png)
![img_2.png](/imgs/img_2.png)

## 🐞 Known Bugs
[Click HERE](KnownBugs.MD)

## 🆘 Need Support?
Visit this link [HERE](https://links.natemarcellus.com) link and join my discord for any questions or support!

## ⚠️ Disclaimer
Please note that using automation tools to interact with websites may violate the terms of service of MissionChief. Make sure to use this bot responsibly and in compliance with the website’s policies.