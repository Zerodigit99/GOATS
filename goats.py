import os
import time
import json
import requests
from datetime import datetime
from colorama import Fore, Style

class Goats:
    def __init__(self):
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.5",
            "Content-Type": "application/json",
            "Origin": "https://dev.goatsbot.xyz",
            "Referer": "https://dev.goatsbot.xyz/",
            "Sec-Ch-Ua": '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }

    def log(self, msg, type='info'):
        timestamp = datetime.now().strftime('%H:%M:%S')
        colors = {
            'success': Fore.GREEN,
            'custom': Fore.MAGENTA,
            'error': Fore.RED,
            'warning': Fore.YELLOW,
            'info': Fore.BLUE
        }
        color = colors.get(type, Fore.BLUE)
        print(f"{color}[{timestamp}] [*] {msg}{Style.RESET_ALL}")

    def countdown(self, seconds):
        for i in range(seconds, -1, -1):
            print(f"\r===== Waiting {i} seconds to continue loop =====", end="")
            time.sleep(1)
        print()

    def login(self, raw_data):
        url = "https://dev-api.goatsbot.xyz/auth/login"
        user_data = json.loads(requests.utils.unquote(raw_data.split('user=')[1].split('&')[0]))
        try:
            response = requests.post(url, headers={**self.headers, 'Rawdata': raw_data})
            if response.status_code == 201:
                data = response.json()['user']
                access_token = response.json()['tokens']['access']['token']
                return {'success': True, 'data': {**data, 'access_token': access_token}, 'user_data': user_data}
            return {'success': False, 'error': 'Login failed'}
        except Exception as e:
            return {'success': False, 'error': f"Error during login: {str(e)}"}

    def get_missions(self, access_token):
        url = "https://api-mission.goatsbot.xyz/missions/user"
        try:
            response = requests.get(url, headers={**self.headers, 'Authorization': f"Bearer {access_token}"})
            if response.status_code == 200:
                data = response.json()
                missions = {'special': [], 'regular': []}
                for category, mission_list in data.items():
                    for mission in mission_list:
                        if category == 'SPECIAL MISSION':
                            missions['special'].append(mission)
                        elif not mission.get('status'):
                            missions['regular'].append(mission)
                return {'success': True, 'missions': missions}
            return {'success': False, 'error': 'Failed to get missions'}
        except Exception as e:
            return {'success': False, 'error': f"Error fetching missions: {str(e)}"}

    def complete_mission(self, mission, access_token):
        if mission['type'] == 'Special':
            now = int(datetime.now().timestamp())
            if 'next_time_execute' in mission and now < mission['next_time_execute']:
                time_left = mission['next_time_execute'] - now
                self.log(f"Mission {mission['name']} is in cooldown: {time_left} seconds", 'warning')
                return False
        url = f"https://dev-api.goatsbot.xyz/missions/action/{mission['_id']}"
        try:
            response = requests.post(url, headers={**self.headers, 'Authorization': f"Bearer {access_token}"})
            return response.status_code == 201
        except Exception:
            return False

    def handle_missions(self, access_token):
        missions_result = self.get_missions(access_token)
        if not missions_result['success']:
            self.log(f"Unable to fetch missions: {missions_result['error']}", 'error')
            return
        for mission in missions_result['missions']['special']:
            self.log(f"Processing special mission: {mission['name']}", 'info')
            result = self.complete_mission(mission, access_token)
            if result:
                self.log(f"Successfully completed mission {mission['name']} | Reward: {mission['reward']}", 'success')
            else:
                self.log(f"Failed to complete mission {mission['name']}", 'error')
        for mission in missions_result['missions']['regular']:
            result = self.complete_mission(mission, access_token)
            if result:
                self.log(f"Successfully completed mission {mission['name']} | Reward: {mission['reward']}", 'success')
            else:
                self.log(f"Failed to complete mission {mission['name']}", 'error')
            time.sleep(1)

    def get_checkin_info(self, access_token):
        url = "https://api-checkin.goatsbot.xyz/checkin/user"
        try:
            response = requests.get(url, headers={**self.headers, 'Authorization': f"Bearer {access_token}"})
            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            return {'success': False, 'error': 'Failed to get check-in info'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def perform_checkin(self, checkin_id, access_token):
        url = f"https://api-checkin.goatsbot.xyz/checkin/action/{checkin_id}"
        try:
            response = requests.post(url, headers={**self.headers, 'Authorization': f"Bearer {access_token}"})
            return response.status_code == 201
        except Exception:
            return False

    def handle_checkin(self, access_token):
        checkin_info = self.get_checkin_info(access_token)
        if not checkin_info['success']:
            self.log(f"Unable to fetch check-in info: {checkin_info['error']}", 'error')
            return
        last_checkin_time = checkin_info['data']['lastCheckinTime']
        time_since_last_checkin = time.time() - last_checkin_time / 1000
        if time_since_last_checkin < 86400:
            self.log("Not enough time since last check-in", 'warning')
            return
        next_checkin = next((day for day in checkin_info['data']['result'] if not day['status']), None)
        if next_checkin:
            if self.perform_checkin(next_checkin['_id'], access_token):
                self.log(f"Successfully checked in on day {next_checkin['day']} | Reward: {next_checkin['reward']}", 'success')
            else:
                self.log(f"Failed to check in on day {next_checkin['day']}", 'error')

    def main(self):
        data_file = os.path.join(os.path.dirname(__file__), 'data.txt')
        with open(data_file, 'r') as f:
            data = [line.strip() for line in f if line.strip()]
        while True:
            for i, init_data in enumerate(data):
                user_data = json.loads(requests.utils.unquote(init_data.split('user=')[1].split('&')[0]))
                first_name = user_data.get('first_name', 'Unknown')
                self.log(f"========== Account {i + 1} | {first_name} ==========", 'info')
                login_result = self.login(init_data)
                if not login_result['success']:
                    self.log(f"Login failed for {first_name}: {login_result['error']}", 'error')
                    continue
                access_token = login_result['data']['access_token']
                self.handle_checkin(access_token)
                self.handle_missions(access_token)
                self.countdown(60)

if __name__ == '__main__':
    goats = Goats()
    goats.main()
