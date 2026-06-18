function overlord:demand/restore_bonds
scoreboard players set #failStreak ovGlobal 0
# A sacrifice paid from the saved pool spends that pool on success.
execute if score #demandKind ovGlobal matches 4 if score #sacSource ovGlobal matches 1 run scoreboard players operation #favorPool ovGlobal -= #demandThreshold ovGlobal
execute if score #demandKind ovGlobal matches 4 run function overlord:favor/show_bar
execute as @a run scoreboard players add @s ovFavor 5
data modify storage overlord:bridge demandResult set value "met"
scoreboard players add #seqDemand ovGlobal 1
execute store result storage overlord:bridge seqDemand int 1 run scoreboard players get #seqDemand ovGlobal
function overlord:demand/cleanup
playsound minecraft:ui.toast.challenge_complete master @a ~ ~ ~ 1 1
tellraw @a {"text":"[Overlord] The demand is met. You live to serve another day.","color":"green","italic":true}
