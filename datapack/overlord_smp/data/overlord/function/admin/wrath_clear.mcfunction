# Hard reset of the wrath system: zero the meter, stop any surge, strip the named
# attribute modifiers off every buffed mob (the attribute command is single-target,
# so iterate), untag them, kill outstanding surge mobs, and hide the bar.
scoreboard players set #wrath ovGlobal 0
scoreboard players set #surgeTimer ovGlobal 0
scoreboard players set #surgeBeat ovGlobal 0
data modify storage overlord:wrath set value {level:0,dmg:"0",hp:"0",radius:48,color:"white",label:"Dormant"}
execute as @e[tag=ov_buffed] run attribute @s minecraft:attack_damage modifier remove overlord:wrath_dmg
execute as @e[tag=ov_buffed] run attribute @s minecraft:max_health modifier remove overlord:wrath_hp
tag @e[tag=ov_buffed] remove ov_buffed
kill @e[tag=ov_surge]
bossbar set overlord:wrath visible false
tellraw @a {"text":"[Overlord] The wrath subsides. The air grows still.","color":"dark_purple","italic":true}
