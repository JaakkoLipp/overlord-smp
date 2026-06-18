# total bled (0.1HP) = d * coeff / 100 ; per recipient = total / k ; hp = per / 10 (integer-HP MVP)
scoreboard players operation #o ovTmp = #d ovTmp
scoreboard players operation #o ovTmp *= #coeff ovGlobal
scoreboard players operation #o ovTmp /= #hundred ovGlobal
scoreboard players operation #per ovTmp = #o ovTmp
scoreboard players operation #per ovTmp /= #k ovTmp
scoreboard players operation #hp ovTmp = #per ovTmp
scoreboard players operation #hp ovTmp /= #ten ovGlobal
execute if score #hp ovTmp matches 1.. run function overlord:soullink/dist_apply
