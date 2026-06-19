bossbar set overlord:wrath visible true
bossbar set overlord:wrath players @a
execute store result bossbar overlord:wrath max run scoreboard players get #wrathMax ovGlobal
execute store result bossbar overlord:wrath value run scoreboard players get #wrath ovGlobal
function overlord:wrath/bar_style with storage overlord:wrath
