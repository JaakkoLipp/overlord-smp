function overlord:demand/restore_bonds
scoreboard players add #failStreak ovGlobal 1
data modify storage overlord:bridge demandResult set value "failed"
scoreboard players add #seqDemand ovGlobal 1
execute store result storage overlord:bridge seqDemand int 1 run scoreboard players get #seqDemand ovGlobal
function overlord:demand/cleanup
tellraw @a {"text":"[Overlord] You have failed me. The price comes due.","color":"dark_red","bold":true}
