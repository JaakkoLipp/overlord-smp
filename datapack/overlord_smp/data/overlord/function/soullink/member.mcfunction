# context: @s = one bonded player. delta is in 0.1 HP units (damage_taken stat granularity).
scoreboard players operation #d ovTmp = @s ovDmgTaken
scoreboard players operation #d ovTmp -= @s ovDmgPrev
scoreboard players operation @s ovDmgPrev = @s ovDmgTaken
execute if score #d ovTmp matches 1.. run function overlord:soullink/bleed {pair:"$(pair)"}
