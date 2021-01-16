import asyncio, re, traceback
from typing import Optional, Set

from irctokens import build, Line
from ircrobots import Bot as BaseBot
from ircrobots import Server as BaseServer

from ircstates.numerics import *
from ircrobots.matching import Response, SELF, ANY, Folded

from ircchallenge import Challenge

from .config import Config
                                         # not having < means it can't be <grant>
RE_OPERNAME = re.compile(r"^is opered as ([^,<]+), privset (\S+)$")

# not in ircstates yet...
RPL_WHOISSPECIAL       = "320"
RPL_RSACHALLENGE2      = "740"
RPL_ENDOFRSACHALLENGE2 = "741"

class Server(BaseServer):
    def __init__(self,
            bot:    BaseBot,
            name:   str,
            config: Config):

        super().__init__(bot, name)
        self._config = config

    async def _oper_name(self, nickname: str):
        await self.send(build("WHOIS", [nickname]))

        whois_oper = Response(RPL_WHOISSPECIAL, [SELF, Folded(nickname)])
        whois_end  = Response(RPL_ENDOFWHOIS,   [SELF, Folded(nickname)])
        #:niven.freenode.net 320 sandcat sandcat :is opered as jess, privset sandcat
        #:niven.freenode.net 318 sandcat sandcat :End of /WHOIS list.

        whois_line = await self.wait_for({
            whois_end, whois_oper
        })
        if whois_line.command == RPL_WHOISSPECIAL:
            await self.wait_for(whois_end)

            match = RE_OPERNAME.search(whois_line.params[2])
            if match is not None:
                return match.group(1)

        return None

    async def _oper_up(self,
            oper_name: str,
            oper_file: str,
            oper_pass: str):

        try:
            challenge = Challenge(keyfile=oper_file, password=oper_pass)
        except Exception:
            traceback.print_exc()
        else:
            await self.send(build("CHALLENGE", [oper_name]))
            challenge_text = Response(RPL_RSACHALLENGE2,      [SELF, ANY])
            challenge_stop = Response(RPL_ENDOFRSACHALLENGE2, [SELF])
            #:niven.freenode.net 740 sandcat :foobarbazmeow
            #:niven.freenode.net 741 sandcat :End of CHALLENGE

            while True:
                challenge_line = await self.wait_for({
                    challenge_text, challenge_stop
                })
                if challenge_line.command == RPL_RSACHALLENGE2:
                    challenge.push(challenge_line.params[1])
                else:
                    retort = challenge.finalise()
                    await self.send(build("CHALLENGE", [f"+{retort}"]))
                    break

    async def line_read(self, line: Line):
        if line.command == RPL_WELCOME:
            oper_name, oper_file, oper_pass = self._config.oper
            await self._oper_up(oper_name, oper_file, oper_pass)

        elif (line.command == "PRIVMSG" and
                self.is_me(line.params[0])):

            nickname = line.hostmask.nickname

            command, *args = line.params[1].lower().split()

            if command == "grantme":
                opername = await self._oper_name(nickname)
                if opername is not None:
                    if not args:
                        await self.send(build("NOTICE", [nickname, "give me an argument then"]))
                    elif not args[0] in self._config.privsets:
                        await self.send(build("NOTICE", [nickname, f"dunno what '{args[0]}' means"]))
                    else:
                        privset = args[0]
                        await self.send(build("GRANT",  [nickname, privset]))
                        await self.send(build("NOTICE", [nickname, f"good luck with {privset} mate"]))
                else:
                    await self.send(build("NOTICE", [nickname, "who are you though"]))

    def line_preread(self, line: Line):
        print(f"{self.name} < {line.format()}")
    def line_presend(self, line: Line):
        print(f"{self.name} > {line.format()}")

class Bot(BaseBot):
    def __init__(self, config: Config):
        super().__init__()
        self._config = config

    def create_server(self, name: str):
        return Server(self, name, self._config)
