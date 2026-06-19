# context: @s = a living player. Each detector sets ovMilestone and bumps the channel.
# First diamond (caught once, then tagged).
execute if entity @s[tag=!ov_diamond,scores={ovDiamond=1..}] run function overlord:milestone/diamond
# First Nether entry.
execute unless entity @s[tag=ov_nether] if dimension minecraft:the_nether run function overlord:milestone/nether
# Sleep: fire each time the sleep stat rises (delta against a per-player baseline).
scoreboard players operation #sd ovTmp = @s ovSleep
scoreboard players operation #sd ovTmp -= @s ovSleepPrev
scoreboard players operation @s ovSleepPrev = @s ovSleep
execute if score #sd ovTmp matches 1.. run function overlord:milestone/sleep
# Idle: block position unchanged for #idleThreshold seconds.
execute store result score #px ovTmp run data get entity @s Pos[0] 1
execute store result score #pz ovTmp run data get entity @s Pos[2] 1
scoreboard players set #moved ovTmp 1
execute if score #px ovTmp = @s ovPosXp if score #pz ovTmp = @s ovPosZp run scoreboard players set #moved ovTmp 0
scoreboard players operation @s ovPosXp = #px ovTmp
scoreboard players operation @s ovPosZp = #pz ovTmp
execute if score #moved ovTmp matches 0 run scoreboard players add @s ovIdle 1
execute if score #moved ovTmp matches 1 run scoreboard players set @s ovIdle 0
execute if score @s ovIdle >= #idleThreshold ovGlobal run function overlord:milestone/idle
