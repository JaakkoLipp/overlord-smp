# context: @s = a player seen for the first time this session. Baseline the sleep stat
# and position so deltas measure only what happens from here on. Suppress "first"
# milestones a returning player has already passed (diamonds owned, already in the Nether)
# so adding the datapack to an existing world does not fire them retroactively.
scoreboard players operation @s ovSleepPrev = @s ovSleep
execute store result score @s ovPosXp run data get entity @s Pos[0] 1
execute store result score @s ovPosZp run data get entity @s Pos[2] 1
scoreboard players set @s ovIdle 0
execute if score @s ovDiamond matches 1.. run tag @s add ov_diamond
execute if dimension minecraft:the_nether run tag @s add ov_nether
tag @s add ov_minit
