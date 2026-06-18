function overlord:demand/restore_bonds
data modify storage overlord:bridge demandResult set value "judge"
scoreboard players add #seqDemand ovGlobal 1
execute store result storage overlord:bridge seqDemand int 1 run scoreboard players get #seqDemand ovGlobal
function overlord:demand/cleanup
tellraw @a {"text":"[Overlord] Your time is spent. I will judge what you have wrought...","color":"dark_purple","italic":true}
