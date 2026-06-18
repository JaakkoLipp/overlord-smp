# context: @s = an item stack on the altar. Add count * #sacWeight to progress, then
# consume the stack (the sacrifice destroys it; it does not feed the favor pool).
execute store result score #c ovTmp run data get entity @s Item.count
scoreboard players operation #c ovTmp *= #sacWeight ovTmp
scoreboard players operation #demandProg ovGlobal += #c ovTmp
kill @s
