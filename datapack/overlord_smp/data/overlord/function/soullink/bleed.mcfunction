# out(0.1HP) = delta * coeff / 100. The bonded partner takes the full share (pairs is
# not split among recipients). Keep it in tenths and hand to the shared receive path,
# which deals it as fractional HP with the death-floor clamp.
scoreboard players operation #o ovTmp = #d ovTmp
scoreboard players operation #o ovTmp *= #coeff ovGlobal
scoreboard players operation #o ovTmp /= #hundred ovGlobal
scoreboard players operation #per ovTmp = #o ovTmp
tag @s add ov_self
execute if score #per ovTmp matches 1.. run function overlord:soullink/apply {pair:"$(pair)"}
tag @s remove ov_self
