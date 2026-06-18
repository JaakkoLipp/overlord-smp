# context: @s = a (living) player, position = @s. delta in 0.1 HP units.
scoreboard players operation #d ovTmp = @s ovDmgTaken
scoreboard players operation #d ovTmp -= @s ovDmgPrev
scoreboard players operation @s ovDmgPrev = @s ovDmgTaken
execute if score #d ovTmp matches 1.. run function overlord:soullink/dist_bleed
