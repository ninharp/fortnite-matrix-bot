#!/usr/bin/env python3

# pylint: disable=broad-except
# pylint: disable=invalid-name
# pylint: disable=missing-docstring
# pylint: disable=no-self-use
# pylint: disable=too-few-public-methods

import asyncio
import os
import re
import sys
import time
import requests
#from markdown import markdown

import nio

class FortniteMatrixBot:
    homeserver = None
    access_token = None
    user_id = None
    accept_invites = None
    proxy = None
    fortnite_data = {}
    fortnite_url = {}
    fortnite_url['br_stats'] = 'https://fortnite-api.com/v2/stats/br/v2'
    intervals = (
    ('weeks', 604800),  # 60 * 60 * 24 * 7
    ('days', 86400),    # 60 * 60 * 24
    ('hours', 3600),    # 60 * 60
    ('minutes', 60),
    ('seconds', 1),
)

    def display_time(self, minutes, granularity=2):
        result = []
        seconds = minutes * 60
        print(minutes)
        print(seconds)
        for name, count in self.intervals:
            value = seconds // count
            if value:
                seconds -= value * count
                if value == 1:
                    name = name.rstrip('s')
                result.append("{} {}".format(value, name))
        return ', '.join(result[:granularity])

    def __init__(self):
        required_env_vars = ['FMB_HOMESERVER', 'FMB_ACCESS_TOKEN', 'FMB_USER_ID']
        for env_var in os.environ:
            if not env_var.startswith('FMB_'):
                continue
            if env_var in required_env_vars:
                required_env_vars.remove(env_var)
            setattr(self, env_var.lower()[4:], os.environ[env_var])
        if required_env_vars:
            raise Exception('missing {}'.format(', '.join(required_env_vars)))
        if self.accept_invites is None:
            self.accept_invites = ':{}$'.format(re.escape(self.user_id.split(':')[1]))

    _client = None

    async def getFortniteStats(self, name):
        query = {'name': name}
        response = requests.get(self.fortnite_url['br_stats'], params=query)
        fn_json = response.json()
        
        if (fn_json["status"] == 404):
            #print("404 - " + fn_json["error"])
            self.fortnite_data = fn_json;
            return False
        if (fn_json["status"] == 200):
            self.fortnite_data = fn_json
            return True

    async def run(self):
        print(f'connecting to {self.homeserver}')
        self._client = nio.AsyncClient(self.homeserver, proxy=self.proxy)
        self._client.access_token = self.access_token
        self._client.user_id = self.user_id
        self._client.device_id = 'FortniteMatrixBot'
        self._client.add_response_callback(self._on_error, nio.SyncError)
        self._client.add_response_callback(self._on_sync, nio.SyncResponse)
        self._client.add_event_callback(self._on_invite, nio.InviteMemberEvent)
        self._client.add_event_callback(self._on_message, nio.RoomMessageText)
        await self._client.sync_forever(timeout=30000)
        await self._client.close()

    async def _on_error(self, response):
        if self._client:
            await self._client.close()
        print(response)
        print('got error, exiting')
        sys.exit(1)

    _initial_sync_done = False

    async def _on_sync(self, _response):
        if not self._initial_sync_done:
            self._initial_sync_done = True
            for room_id in self._client.rooms:
                print(f'joined room {room_id}')
            print('initial sync done, ready for work')

    async def _on_invite(self, room, event):
        if not re.search(self.accept_invites, event.sender, re.IGNORECASE):
            print(f'invite from {event.sender} to {room.room_id} rejected')
            await self._client.room_leave(room.room_id)
        else:
            print(f'invite from {event.sender} to {room.room_id} accepted')
            await self._client.join(room.room_id)

    _last_event_timestamp = time.time() * 1000

    async def _on_message(self, room, event):
        await self._client.update_receipt_marker(room.room_id, event.event_id)
        if event.sender == self._client.user_id:
            return
        if event.server_timestamp <= self._last_event_timestamp:
            return
        self._last_event_timestamp = event.server_timestamp
        regex = '^!(fortnite|fn)'
        if re.search(regex, event.body, re.IGNORECASE):
            if re.search('^!(fortnite|fn)$', event.body, re.IGNORECASE):
                await self._client.room_send(
                    room_id=room.room_id,
                    message_type='m.room.message',
                    content={'msgtype': 'm.text', 'body': '!fortnite ACCOUNTNAME'},
                    ignore_unverified_devices=True)
            elif re.search('^!(fortnite|fn)\s(.*)$', event.body, re.IGNORECASE):
                mo = re.search('^!(fortnite|fn)\s(.*)$', event.body, re.IGNORECASE);
                arg = mo.group(2)
                
                message = """<table width='75%' align='center'>
    <tr><td colspan=2 style='text-align: center;'><img src='mxc://matrix.rtb.rocks/szvkoLXFKmRrvXvpCTtABgDO'></td></tr>
    <tr><td colspan=2 align='center'><font size=6><b>##name##</b>&nbsp;<i>(##id##)</i></font></td></tr>
    <tr><td colspan=2></td></tr>
    <tr><td colspan=2><b>Level ##level## (##progress##%)</b></td></tr>
    <tr><td colspan=2>&nbsp;</td></tr>
    <tr><td colspan=2><font size=5><b>Overall Statistics</b></font></td></tr>
    <tr><td colspan=2 align='center'>
        <table width='100%'>
            <tr><td>Score</td><td align='right'>##score##</td></tr>
            <tr><td>Score per Minute</td><td align='right'>##scorePerMin##</td></tr>
            <tr><td>Score per Match</td><td align='right'>##scorePerMatch##</td></tr>
            <tr><td colspan=2>&nbsp;</td></tr>
            <tr><td>Wins</td><td align='right'>##wins##</td></tr>
            <tr><td>Deaths</td><td align='right'>##deaths##</td></tr>
            <tr><td colspan=2>&nbsp;</td></tr>
            <tr><td>Kills</td><td align='right'>##kills##</td></tr>
            <tr><td>Kills per Minute</td><td align='right'>##killsPerMin##</td></tr>
            <tr><td>Kills per Match</td><td align='right'>##killsPerMatch##</td></tr>
            <tr><td>KD</td><td align='right'>##kd##</td></tr>
            <tr><td colspan=2>&nbsp;</td></tr>
            <tr><td>Matches</td><td align='right'>##matches##</td></tr>
            <tr><td>Win Rate</td><td align='right'>##winRate##</td></tr>
            <tr><td>Players Outlived</td><td align='right'>##playersOutlived##</td></tr>
            <tr><td>Time Played</td><td align='right'>##minutesPlayed##</td></tr>
            <tr><td>Last Modified</td><td align='right'>##lastModified##</td></tr>
            <tr><td colspan=2>&nbsp;</td></tr>
            <tr><td>Top 3</td><td align='right'>##top3##</td></tr>
            <tr><td>Top 5</td><td align='right'>##top5##</td></tr>
            <tr><td>Top 6</td><td align='right'>##top6##</td></tr>
            <tr><td>Top 10</td><td align='right'>##top10##</td></tr>
            <tr><td>Top 10</td><td align='right'>##top12##</td></tr>
            <tr><td>Top 25</td><td align='right'>##top25##</td></tr>
        </table>
    </td></tr>
</table>"""
                
                if (await self.getFortniteStats(arg)):
                    try:
                        if (self.fortnite_data["status"] == 200):
                            self.fortnite_data = self.fortnite_data["data"]
                            account = self.fortnite_data["account"]
                            battlePass = self.fortnite_data["battlePass"]
                            
                            stats = self.fortnite_data["stats"]
                            stats_overall = stats["all"]["overall"]
                            #stats_solo = stats["all"]["solo"]
                            #stats_duo = stats["all"]["duo"]
                            #stats_squad = stats["all"]["squad"]
                            #stats_ltm = stats["all"]["ltm"]
                            message = message.replace("##level##", str(battlePass["level"]))
                            message = message.replace("##progress##", str(battlePass["progress"]))
                            message = message.replace("##name##", str(account["name"]))
                            message = message.replace("##id##", str(account["id"]))

                            stats_overall["minutesPlayed"] = self.display_time(stats_overall["minutesPlayed"])

                            for key in stats_overall:
                                message = message.replace("##" +str(key)+ "##", str(stats_overall[key]))
                            
                            content = {'msgtype': 'm.text'}
                            #formatted_message = markdown(message)
                            formatted_message = message
                            content["format"] = "org.matrix.custom.html"
                            content["formatted_body"] = formatted_message
                            content["body"] = message
                            print(f'sending message to {room.room_id}')
                            await self._client.room_typing(room.room_id, True)
                            await self._client.room_send(
                                room_id=room.room_id,
                                message_type='m.room.message',
                                content=content,
                                ignore_unverified_devices=True)
                            await self._client.room_typing(room.room_id, False)
                    except:
                        await self._client.room_send(
                            room_id=room.room_id,
                            message_type='m.room.message',
                            content={'msgtype': 'm.text', 'body': 'Undefined Error'},
                            ignore_unverified_devices=True)
                        print("KeyError")
                else:
                    try:
                        error = self.fortnite_data["error"]
                        print("Error: "+error)
                        await self._client.room_send(
                            room_id=room.room_id,
                            message_type='m.room.message',
                            content={'msgtype': 'm.text', 'body': 'Error '+error},
                            ignore_unverified_devices=True)
                    except:
                        print("Unknown error")
                    

if __name__ == '__main__':
    asyncio_debug = False
    if 'FMB_DEBUG' in os.environ:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        asyncio_debug = True
    try:
        FMB = FortniteMatrixBot()
        asyncio.run(FMB.run(), debug=asyncio_debug)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(e)
        print('got exception, exiting')
        sys.exit(1)
