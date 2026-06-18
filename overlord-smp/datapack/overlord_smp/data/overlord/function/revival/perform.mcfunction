# context: @s = reviver who can afford it.
scoreboard players operation #cost ovTmp = #revivalXp ovGlobal
execute store result storage overlord:tmp lvl int 1 run scoreboard players get #cost ovTmp
function overlord:revival/charge with storage overlord:tmp
# consume one totem on any altar
execute as @e[type=marker,tag=ov_altar] at @s run kill @e[type=item,distance=..3,nbt={Item:{id:"minecraft:totem_of_undying"}},limit=1]
# return one fallen player (most-arbitrary; tune selection as desired)
execute as @a[tag=ov_dead,limit=1] run function overlord:revival/restore
tellraw @a [{"text":"A life is bought back from the dark. ","color":"light_purple"},{"selector":"@s"},{"text":" paid the price.","color":"gray"}]
