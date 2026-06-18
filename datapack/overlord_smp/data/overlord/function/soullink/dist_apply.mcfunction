# Deal #hp HP to each recipient and pre-advance their baseline by the same amount
# (anti-feedback: bled damage must not re-bleed). Recipient set depends on mode.
scoreboard players operation #adj ovTmp = #hp ovTmp
scoreboard players operation #adj ovTmp *= #ten ovGlobal
execute store result storage overlord:tmp amt int 1 run scoreboard players get #hp ovTmp
execute store result storage overlord:tmp r int 1 run scoreboard players get #linkRadius ovGlobal
execute if score #linkMode ovGlobal matches 1 run function overlord:soullink/apply_global with storage overlord:tmp
execute if score #linkMode ovGlobal matches 2 run function overlord:soullink/apply_near with storage overlord:tmp
