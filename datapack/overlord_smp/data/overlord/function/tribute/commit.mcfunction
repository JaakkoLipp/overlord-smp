# context: @s = altar marker. Tribute = stack count + weighted valuables.
scoreboard players set #trib ovTmp 0
execute store result score #n ovTmp if entity @e[type=item,distance=..3]
scoreboard players operation #trib ovTmp += #n ovTmp
execute store result score #v ovTmp if entity @e[type=item,distance=..3,nbt={Item:{id:"minecraft:diamond"}}]
scoreboard players operation #v ovTmp *= #three ovGlobal
scoreboard players operation #trib ovTmp += #v ovTmp
execute store result score #v ovTmp if entity @e[type=item,distance=..3,nbt={Item:{id:"minecraft:netherite_ingot"}}]
scoreboard players operation #v ovTmp *= #ten ovGlobal
scoreboard players operation #trib ovTmp += #v ovTmp
# Award to nearest player (the donor). ovTribute is consumed by the bridge; ovFavor is the running ledger.
execute as @p[distance=..12] run scoreboard players operation @s ovTribute += #trib ovTmp
execute as @p[distance=..12] run scoreboard players operation @s ovFavor += #trib ovTmp
kill @e[type=item,distance=..3]
tellraw @a {"text":"[Overlord] A tribute is received. The presence deliberates...","color":"dark_purple","italic":true}
# Bump the bridge tribute sequence so the Python overlord wakes up.
scoreboard players add #seqTribute ovGlobal 1
execute store result storage overlord:bridge seqTribute int 1 run scoreboard players get #seqTribute ovGlobal
