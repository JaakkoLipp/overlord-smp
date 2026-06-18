scoreboard players remove #demandTimer ovGlobal 1
execute if score #demandKind ovGlobal matches 0 run function overlord:demand/measure_score
execute if score #demandKind ovGlobal matches 1 run function overlord:demand/measure_altar
function overlord:demand/update_bar
function overlord:demand/phases
execute if score #demandActive ovGlobal matches 1 unless score #demandKind ovGlobal matches 2 if score #demandProg ovGlobal >= #demandThreshold ovGlobal run function overlord:demand/succeed
execute if score #demandActive ovGlobal matches 1 if score #demandTimer ovGlobal matches ..0 run function overlord:demand/deadline
