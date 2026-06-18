scoreboard players set #demandPhase ovGlobal 3
scoreboard players set #coeff ovGlobal 80
bossbar set overlord:demand color purple
bossbar set overlord:demand name [{"text":"\u26a0 THE RECKONING \u26a0","color":"dark_purple","bold":true}]
title @a times 5 50 10
title @a subtitle {"text":"Deliver now, or pay in blood","color":"dark_red"}
title @a title {"text":"RECKONING","color":"dark_purple","bold":true}
playsound minecraft:entity.wither.spawn master @a ~ ~ ~ 1 0.6
tellraw @a {"text":"[Overlord] Time is gone. A reckoning is upon you.","color":"dark_purple","bold":true}
