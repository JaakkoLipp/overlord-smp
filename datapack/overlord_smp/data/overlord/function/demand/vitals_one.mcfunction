# context: @s = a living player. Fold this player's health into the running minimum.
execute store result score #curHp ovTmp run data get entity @s Health
scoreboard players operation #minHp ovTmp < #curHp ovTmp
