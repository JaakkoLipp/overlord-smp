# context: @s = an ov_altar marker. Consume the valuables offered on it, adding their
# weighted worth to demand progress. Rarer items are worth more. Set the weight, then
# fold each matching stack's count into progress via sac_add (which kills the stack).
scoreboard players set #sacWeight ovTmp 1
execute as @e[type=item,distance=..3,nbt={Item:{id:"minecraft:gold_ingot"}}] run function overlord:demand/sac_add
scoreboard players set #sacWeight ovTmp 9
execute as @e[type=item,distance=..3,nbt={Item:{id:"minecraft:gold_block"}}] run function overlord:demand/sac_add
scoreboard players set #sacWeight ovTmp 2
execute as @e[type=item,distance=..3,nbt={Item:{id:"minecraft:emerald"}}] run function overlord:demand/sac_add
scoreboard players set #sacWeight ovTmp 3
execute as @e[type=item,distance=..3,nbt={Item:{id:"minecraft:diamond"}}] run function overlord:demand/sac_add
scoreboard players set #sacWeight ovTmp 27
execute as @e[type=item,distance=..3,nbt={Item:{id:"minecraft:diamond_block"}}] run function overlord:demand/sac_add
scoreboard players set #sacWeight ovTmp 10
execute as @e[type=item,distance=..3,nbt={Item:{id:"minecraft:netherite_ingot"}}] run function overlord:demand/sac_add
scoreboard players set #sacWeight ovTmp 90
execute as @e[type=item,distance=..3,nbt={Item:{id:"minecraft:netherite_block"}}] run function overlord:demand/sac_add
scoreboard players set #sacWeight ovTmp 8
execute as @e[type=item,distance=..3,nbt={Item:{id:"minecraft:totem_of_undying"}}] run function overlord:demand/sac_add
