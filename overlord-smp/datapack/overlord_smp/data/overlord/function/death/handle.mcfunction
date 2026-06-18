# context: @s = a player whose deathCount just incremented.
scoreboard players set @s ovDeaths 0
tag @s add ov_dead
gamemode spectator @s
title @s times 10 60 20
title @s subtitle {"text":"Only a ritual can call you back","color":"gray"}
title @s title {"text":"You have fallen","color":"dark_red"}
tellraw @a [{"selector":"@s","color":"red"},{"text":" has died. The living must decide.","color":"gray"}]
