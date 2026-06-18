$scoreboard players set #demandKind ovGlobal $(kind)
$scoreboard players set #demandThreshold ovGlobal $(threshold)
$scoreboard players set #demandTimer ovGlobal $(seconds)
$scoreboard players set #demandMax ovGlobal $(seconds)
$scoreboard players set #demandOvertime ovGlobal $(overtime)
$scoreboard players set #sacSource ovGlobal $(source)
scoreboard players set #demandProg ovGlobal 0
scoreboard players set #demandPhase ovGlobal 0
scoreboard players operation #demandHalf ovGlobal = #demandMax ovGlobal
scoreboard players operation #demandHalf ovGlobal /= #two ovGlobal
scoreboard players operation #demandQuarter ovGlobal = #demandMax ovGlobal
scoreboard players operation #demandQuarter ovGlobal /= #four ovGlobal
execute if score #demandKind ovGlobal matches 0 run function overlord:demand/baseline
bossbar remove overlord:demand
bossbar add overlord:demand {"text":"Demand"}
execute store result bossbar overlord:demand max run scoreboard players get #demandMax ovGlobal
execute store result bossbar overlord:demand value run scoreboard players get #demandTimer ovGlobal
bossbar set overlord:demand color yellow
bossbar set overlord:demand style notched_10
bossbar set overlord:demand players @a
bossbar set overlord:demand visible true
scoreboard players set #demandActive ovGlobal 1
scoreboard players set #secCounter ovGlobal 0
function overlord:demand/update_bar
# Kind-specific setup that needs the bar already raised.
execute if score #demandKind ovGlobal matches 3 run function overlord:demand/survive_begin
execute if score #demandKind ovGlobal matches 4 run function overlord:demand/sacrifice_begin
