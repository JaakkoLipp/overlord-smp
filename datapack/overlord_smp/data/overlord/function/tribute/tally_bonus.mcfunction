# context: @s = a valuable item stack. Add an extra (count * #tribW) on top of the base
# tally, so rarer items are weighted by their real quantity.
execute store result score #c ovTmp run data get entity @s Item.count
scoreboard players operation #c ovTmp *= #tribW ovTmp
scoreboard players operation #trib ovTmp += #c ovTmp
