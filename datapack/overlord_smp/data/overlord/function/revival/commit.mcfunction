# context: @s = candidate reviver.
execute store result score #lvl ovTmp run experience query @s levels
execute if score #lvl ovTmp >= #revivalXp ovGlobal run function overlord:revival/perform
