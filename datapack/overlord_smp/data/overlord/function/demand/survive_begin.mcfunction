# context: run once when a survive ordeal begins (bar already raised). Baseline the
# death tally, save the soul-link coefficient for restoration, and raise the shared
# vitals bar so the group watches one number: their weakest member's health.
execute store result score #surviveBaseDeaths ovGlobal run scoreboard players get #deathTally ovGlobal
scoreboard players operation #coeffSaved ovGlobal = #coeff ovGlobal
scoreboard players set #surgeBeat ovGlobal 0
bossbar set overlord:demand name [{"text":"☠ ENDURE: keep everyone alive ☠","color":"dark_red","bold":true}]
bossbar set overlord:demand color red
bossbar set overlord:vitals players @a
bossbar set overlord:vitals visible true
function overlord:demand/vitals
tellraw @a {"text":"[Overlord] An ordeal begins. Should even one of you fall, all are forsaken. Endure.","color":"dark_red","bold":true}
playsound minecraft:entity.wither.spawn master @a ~ ~ ~ 1 0.5
