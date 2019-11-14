import asyncio
import os
from asyncio.subprocess import PIPE, STDOUT


async def run(cmd):
    p = await asyncio.create_subprocess_shell(
        cmd,
        stdin=PIPE,
        stdout=PIPE,
        stderr=STDOUT
    )
    stdout, stderr = await p.communicate()
    code = p.returncode

    if stdout:
        stdout = stdout.decode("utf-8")
    if stderr:
        stderr = stderr.decode("utf-8")

    return stdout, stderr, code


async def get_temp():
    if os.name == "posix":
        out, _, code = await run("vcgencmd measure_temp")
        if code:  # non-zero
            return "-"
        return ((out.replace("temp=", "")).strip("\n "))
    else:
        return "-"


async def get_linecount():
    if os.name == "posix":
        out, _, code = await run("find . -name '*.py' | xargs wc -l | tail -n 1")
        if code:  # non-zero
            return "-"
        return (out.strip()).split()[0]
    else:
        return "-"
