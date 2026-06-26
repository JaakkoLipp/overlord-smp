# Deliver #per (0.1HP) to each recipient through the shared receive path (death-floor
# clamp + per-recipient anti-feedback baseline advance + fractional damage). Recipient
# set depends on mode: global = all living others, proximity = living others in radius.
execute if score #linkMode ovGlobal matches 1 run function overlord:soullink/apply_global
execute store result storage overlord:tmp r int 1 run scoreboard players get #linkRadius ovGlobal
execute if score #linkMode ovGlobal matches 2 run function overlord:soullink/apply_near with storage overlord:tmp
