# total bled (0.1HP) = d * coeff / 100 ; per recipient = total / k (0.1HP).
# Keep the per-recipient share in tenths and hand it to the receive path, which deals it
# as fractional HP. Gating on #per >= 1 means any share of at least 0.1 HP is delivered;
# the old code floored per/10 to whole HP first, so typical combat damage vanished.
scoreboard players operation #o ovTmp = #d ovTmp
scoreboard players operation #o ovTmp *= #coeff ovGlobal
scoreboard players operation #o ovTmp /= #hundred ovGlobal
scoreboard players operation #per ovTmp = #o ovTmp
scoreboard players operation #per ovTmp /= #k ovTmp
execute if score #per ovTmp matches 1.. run function overlord:soullink/dist_apply
