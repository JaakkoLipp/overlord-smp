# Run as a player to consecrate an altar at your feet.
summon minecraft:marker ~ ~ ~ {Tags:["ov_altar"]}
tellraw @s {"text":"[Overlord] Altar consecrated at your position.","color":"dark_purple"}
