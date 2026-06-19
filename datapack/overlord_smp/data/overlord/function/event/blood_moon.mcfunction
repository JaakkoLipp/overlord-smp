# A combo event: night plus a spawn surge plus dramatic framing.
time set night
$scoreboard players set #surgeTimer ovGlobal $(duration)
$scoreboard players set #surgeCadence ovGlobal $(cadence)
$scoreboard players set #surgeCap ovGlobal $(cap)
scoreboard players set #surgeBeat ovGlobal 0
function overlord:wrath/surge
title @a times 10 60 20
title @a subtitle {"text":"The blood moon rises","color":"dark_red"}
title @a title {"text":"☾ BLOOD MOON ☾","color":"red","bold":true}
playsound minecraft:entity.wither.spawn master @a ~ ~ ~ 1 0.5
tellraw @a {"text":"[Overlord] A blood moon rises. The night will not spare you.","color":"dark_red","bold":true}
