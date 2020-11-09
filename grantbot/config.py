from dataclasses import dataclass
from os.path     import expanduser
from typing      import List, Tuple

import yaml

@dataclass
class Config(object):
    nickname: str
    username: str
    realname: str
    password: str

    sasl: Tuple[str, str]
    oper: Tuple[str, str]

    server:   Tuple[str, int, bool]
    privsets: List[str]

def load(filepath: str):
    with open(filepath) as file:
        config_yaml = yaml.safe_load(file.read())

    nickname = config_yaml["nickname"]

    server   = config_yaml["server"]
    hostname, port_s = server.split(":", 1)
    tls      = False

    if port_s.startswith("+"):
        tls    = True
        port_s = port_s.lstrip("+")
    port = int(port_s)

    oper_name = config_yaml["oper"]["name"]
    oper_file = expanduser(config_yaml["oper"]["file"])
    oper_pass = config_yaml["oper"]["pass"]

    return Config(
        nickname,
        config_yaml.get("username", nickname),
        config_yaml.get("realname", nickname),
        config_yaml["password"],
        (config_yaml["sasl"]["username"], config_yaml["sasl"]["password"]),
        (oper_name, oper_file, oper_pass),
        (hostname, port, tls),
        config_yaml["privsets"]
    )
