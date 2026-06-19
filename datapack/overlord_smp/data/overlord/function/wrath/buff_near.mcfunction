# context: @s = a player, position = @s. Buff every nearby hostile not yet buffed.
# The radius bounds the world-scan so it never sweeps the whole world.
$execute as @e[type=#overlord:hostiles,tag=!ov_buffed,distance=..$(radius)] run function overlord:wrath/buff_one with storage overlord:wrath
