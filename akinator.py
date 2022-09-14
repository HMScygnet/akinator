from .utils import Switch, Akinator
from datetime import datetime, timedelta
from asyncio import sleep

from hoshino import Service
from hoshino.typing import CQEvent
from hoshino.typing import MessageSegment as Seg

import aiohttp
aki = Akinator()
sv = Service('akinator')


yes = ['是', '是的', '对', '有', '在','yes', 'y', '1']
no = ['不是','不','不对','否', '没有', '不在', 'no','n','2']
idk = ['我不知道','不知道','不清楚','idk','3']
probably = ['可能是','也许是', '或许是', '应该是', '大概是', '4']
probablyn = ['可能不是','也许不是','或许不是', '应该不是', '大概不是','5']
back = ['返回','上一个','b','B']

sw = Switch()
client_session = aiohttp.ClientSession()

@sv.on_fullmatch('网络天才')
async def akinator_start(bot, ev: CQEvent):
    uid = ev.user_id
    gid = ev.group_id
    if sw.get_on_off_status(gid):
        if uid == sw.on[gid]:
            sw.timeout[gid] = datetime.now()+timedelta(seconds=30)
            await bot.finish(ev, f"您已经开始游戏啦")
        else:
            await bot.finish(ev, f"本群[CQ:at,qq={sw.on[gid]}]正在玩，请耐心等待~")
    
    try:
        r = await aki.start_game(language='cn',client_session=client_session)
        q = r['question']
        sw.turn_on(gid, uid, r)
    except Exception as e:
        await bot.send(ev,f'服务器出问题了，一会再来玩吧\n{e}')
        return
    await bot.send(ev,q)
    await sleep(30)
    ct = 0
    while sw.get_on_off_status(gid):
        if datetime.now() < sw.timeout[gid]:
            if ct != sw.count[gid]:
                ct = sw.count[gid]
                sw.timeout[gid] = datetime.now()+timedelta(seconds=60)
        else:
            temp = sw.on[gid]
            await bot.send(ev, f"[CQ:at,qq={temp}] 由于超时，已为您自动结束游戏")
            sw.turn_off(gid)
            break
        await sleep(30)
    return

@sv.on_message('group')
async def answer_question(bot, ev: CQEvent):
    if sw.get_on_off_status(ev.group_id) is False:
        return
    uid = ev.user_id
    gid = ev.group_id
    if not(uid == int(sw.on[gid])):
        return
    
    reply = ev.message.extract_plain_text()
    try:
        if reply in yes:
            r = await aki.answer('0',sw.aki[gid])
        elif reply in no:
            r = await aki.answer('1',sw.aki[gid])
        elif reply in idk:
            r = await aki.answer('2',sw.aki[gid])
        elif reply in probably:
            r = await aki.answer('3',sw.aki[gid])
        elif reply in probablyn:
            r = await aki.answer('4',sw.aki[gid])
        elif reply in back:
            r = await aki.back(sw.aki[gid])
        else:
            return
        q = r['question']
        sw.count_plus(gid, r)
    except Exception as e:
        await bot.send(ev,f'服务器出问题了，一会再来玩吧\n{e}')
        sw.turn_off(gid)
        return
    
    if r['progression'] > 80:
        answer = await aki.win(sw.aki[gid])
        msg = f"是 {answer['name']} ({answer['description']})! 我猜对了么?"+Seg.image(answer['absolute_picture_path'])
        await bot.send(ev,msg)
        sw.turn_off(gid)
        return
    else:
        await bot.send(ev,q)
        

@sv.on_fullmatch('结束网络天才')
async def akinator_end(bot,ev: CQEvent):
    gid = ev.group_id
    if sw.get_on_off_status(gid):
        if sw.on[gid] != ev.user_id:
            await bot.send(ev, '不能替别人结束游戏哦～')
            return
    sw.turn_off(gid)
    await bot.send(ev,'已结束')