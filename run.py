import asyncio
import sys

from katbot import KatBOT, setup_log
from katbot.cogs.utils import datapath_container

if __name__ == "__main__":
    datapath_container.setfile(__file__)

    if "win" in sys.platform:
        asyncio.set_event_loop(asyncio.ProactorEventLoop())

    with setup_log():
        KatBOT()()
