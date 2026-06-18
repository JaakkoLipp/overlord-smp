scoreboard players add #secCounter ovGlobal 1
execute if score #secCounter ovGlobal matches 20.. run scoreboard players set #secCounter ovGlobal 0
execute if score #secCounter ovGlobal matches 0 run function overlord:demand/second
