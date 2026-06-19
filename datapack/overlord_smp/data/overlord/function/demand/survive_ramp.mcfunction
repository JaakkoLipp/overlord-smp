# The world turns deadlier as the ordeal clock falls. Phase is set by the shared
# demand phases (0 above half, 1 below half, 2 below quarter). Two instruments climb
# together: the soul-link coefficient (shared pain) and the spawn surge (hordes).
execute if score #demandPhase ovGlobal matches 0 run scoreboard players set #coeff ovGlobal 40
execute if score #demandPhase ovGlobal matches 1 run scoreboard players set #coeff ovGlobal 60
execute if score #demandPhase ovGlobal matches 2 run scoreboard players set #coeff ovGlobal 80
execute if score #demandPhase ovGlobal matches 3.. run scoreboard players set #coeff ovGlobal 95
execute if score #demandPhase ovGlobal matches 0 run scoreboard players set #surgeCadence ovGlobal 10
execute if score #demandPhase ovGlobal matches 1 run scoreboard players set #surgeCadence ovGlobal 7
execute if score #demandPhase ovGlobal matches 2.. run scoreboard players set #surgeCadence ovGlobal 5
execute if score #demandPhase ovGlobal matches 0 run scoreboard players set #surgeCap ovGlobal 6
execute if score #demandPhase ovGlobal matches 1 run scoreboard players set #surgeCap ovGlobal 9
execute if score #demandPhase ovGlobal matches 2.. run scoreboard players set #surgeCap ovGlobal 12
scoreboard players add #surgeBeat ovGlobal 1
execute if score #surgeBeat ovGlobal >= #surgeCadence ovGlobal run function overlord:wrath/surge_beat
