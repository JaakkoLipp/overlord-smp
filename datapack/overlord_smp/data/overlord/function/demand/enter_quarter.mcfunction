scoreboard players set #demandPhase ovGlobal 2
bossbar set overlord:demand color red
# Survive ordeals manage the coefficient themselves (saved at begin, ramped each
# second), so skip the standard quarter-time spike for them to avoid double-saving.
execute unless score #demandKind ovGlobal matches 3 run scoreboard players operation #coeffSaved ovGlobal = #coeff ovGlobal
execute unless score #demandKind ovGlobal matches 3 run scoreboard players set #coeff ovGlobal 60
playsound minecraft:block.note_block.didgeridoo master @a ~ ~ ~ 1 0.5
tellraw @a {"text":"[Overlord] The bonds tighten. Your fates draw closer as the end nears.","color":"red","italic":true}
