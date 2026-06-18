# Anti-feedback: pre-advance the partner's baseline by the damage we are about to deal,
# so the magic damage we inflict does NOT itself bleed back next iteration (ping-pong loop).
scoreboard players operation #adj ovTmp = #hp ovTmp
scoreboard players operation #adj ovTmp *= #ten ovGlobal
execute store result storage overlord:tmp amt int 1 run scoreboard players get #hp ovTmp
$execute as @a[tag=$(pair),tag=!ov_self] run scoreboard players operation @s ovDmgPrev += #adj ovTmp
$execute as @a[tag=$(pair),tag=!ov_self] run function overlord:soullink/hurt with storage overlord:tmp
