# context: @s = the revived player.
tag @s remove ov_dead
gamemode survival @s
effect give @s minecraft:regeneration 10 1
effect give @s minecraft:resistance 10 4
execute at @e[type=marker,tag=ov_altar,limit=1] run tp @s @e[type=marker,tag=ov_altar,limit=1]
title @s title {"text":"Returned","color":"green"}
