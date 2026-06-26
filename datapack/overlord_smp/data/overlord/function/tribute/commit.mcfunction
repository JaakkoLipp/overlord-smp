# context: @s = altar marker. Tribute = total item COUNT + weighted valuables, summed
# over real stack quantities (not one point per dropped stack).
scoreboard players set #trib ovTmp 0
execute as @e[type=item,distance=..3] run function overlord:tribute/tally_one
# Weighted bonuses, added on top per item: diamonds +3 each, netherite +10 each.
scoreboard players set #tribW ovTmp 3
execute as @e[type=item,distance=..3,nbt={Item:{id:"minecraft:diamond"}}] run function overlord:tribute/tally_bonus
scoreboard players set #tribW ovTmp 10
execute as @e[type=item,distance=..3,nbt={Item:{id:"minecraft:netherite_ingot"}}] run function overlord:tribute/tally_bonus
# Award to nearest player (the donor). ovTribute is consumed by the bridge; ovFavor is the running ledger.
execute as @p[distance=..12] run scoreboard players operation @s ovTribute += #trib ovTmp
execute as @p[distance=..12] run scoreboard players operation @s ovFavor += #trib ovTmp
# Every tribute also feeds the communal favor pool: one shared number the group fills.
scoreboard players operation #favorPool ovGlobal += #trib ovTmp
function overlord:favor/show_bar
kill @e[type=item,distance=..3]
tellraw @a {"text":"[Overlord] A tribute is received. The presence deliberates...","color":"dark_purple","italic":true}
# Bump the bridge tribute sequence so the Python overlord wakes up.
scoreboard players add #seqTribute ovGlobal 1
execute store result storage overlord:bridge seqTribute int 1 run scoreboard players get #seqTribute ovGlobal
