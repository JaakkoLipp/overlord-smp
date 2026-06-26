# context: @s = recipient ; #per ovTmp = intended bleed in 0.1 HP units.
# Shared receive path for every link mode (pairs / global / proximity). Three jobs:
#   1. Death floor: link damage may never drop @s below #linkFloor (0.1 HP). Clamp the
#      bleed to the headroom above the floor (so one big hit can no longer chain-wipe).
#   2. Anti-feedback: pre-advance @s baseline by the ACTUAL dealt amount, so this magic
#      damage does not itself re-bleed next iteration (no ping-pong).
#   3. Fractional delivery: deal the bleed as decimal HP so sub-1HP shares are not lost
#      to integer rounding (the old /10 floor zeroed out typical combat damage).
execute store result score #hpNow ovTmp run data get entity @s Health 10
scoreboard players operation #avail ovTmp = #hpNow ovTmp
scoreboard players operation #avail ovTmp -= #linkFloor ovGlobal
scoreboard players set #dealt ovTmp 0
execute if score #avail ovTmp matches 1.. run scoreboard players operation #dealt ovTmp = #per ovTmp
execute if score #dealt ovTmp > #avail ovTmp run scoreboard players operation #dealt ovTmp = #avail ovTmp
execute unless score #dealt ovTmp matches 1.. run return fail
scoreboard players operation @s ovDmgPrev += #dealt ovTmp
scoreboard players operation #whole ovTmp = #dealt ovTmp
scoreboard players operation #whole ovTmp /= #ten ovGlobal
scoreboard players operation #frac ovTmp = #dealt ovTmp
scoreboard players operation #frac ovTmp %= #ten ovGlobal
execute store result storage overlord:tmp whole int 1 run scoreboard players get #whole ovTmp
execute store result storage overlord:tmp frac int 1 run scoreboard players get #frac ovTmp
function overlord:soullink/recv_dmg with storage overlord:tmp
