# context: @s = an item stack on the altar. Add its actual stack COUNT to the tribute
# tally (not 1 per stack), so dropping 64 of something is worth 64, not 1.
execute store result score #c ovTmp run data get entity @s Item.count
scoreboard players operation #trib ovTmp += #c ovTmp
