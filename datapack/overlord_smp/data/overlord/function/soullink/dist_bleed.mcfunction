# context: @s = source, position = source, #d = delta (0.1 HP). Count recipients by mode.
tag @s add ov_self
scoreboard players set #k ovTmp 0
execute if score #linkMode ovGlobal matches 1 store result score #k ovTmp if entity @a[tag=!ov_self,tag=!ov_dead]
execute if score #linkMode ovGlobal matches 2 run function overlord:soullink/count_near_store
execute if score #k ovTmp matches 1.. run function overlord:soullink/dist_split
tag @s remove ov_self
