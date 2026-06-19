execute store result bossbar overlord:demand value run scoreboard players get #demandTimer ovGlobal
# Survive ordeals keep their static "ENDURE" name (no progress counter); every other
# kind shows the live progress / threshold in the bar name.
execute unless score #demandKind ovGlobal matches 3 run function overlord:demand/bar_name with storage overlord:demand
