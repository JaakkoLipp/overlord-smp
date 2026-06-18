scoreboard players set #demandPhase ovGlobal 2
bossbar set overlord:demand color red
scoreboard players operation #coeffSaved ovGlobal = #coeff ovGlobal
scoreboard players set #coeff ovGlobal 60
playsound minecraft:block.note_block.didgeridoo master @a ~ ~ ~ 1 0.5
tellraw @a {"text":"[Overlord] The bonds tighten. Your fates draw closer as the end nears.","color":"red","italic":true}
