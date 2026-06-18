# out(0.1HP) = delta * coeff / 100 ; hp = out / 10 (integer-HP granularity for MVP)
scoreboard players operation #o ovTmp = #d ovTmp
scoreboard players operation #o ovTmp *= #coeff ovGlobal
scoreboard players operation #o ovTmp /= #hundred ovGlobal
scoreboard players operation #hp ovTmp = #o ovTmp
scoreboard players operation #hp ovTmp /= #ten ovGlobal
tag @s add ov_self
execute if score #hp ovTmp matches 1.. run function overlord:soullink/apply {pair:"$(pair)"}
tag @s remove ov_self
