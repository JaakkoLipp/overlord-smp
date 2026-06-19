scoreboard players remove #demandTimer ovGlobal 1
execute if score #demandKind ovGlobal matches 0 run function overlord:demand/measure_score
execute if score #demandKind ovGlobal matches 1 run function overlord:demand/measure_altar
execute if score #demandKind ovGlobal matches 3 run function overlord:demand/measure_survive
execute if score #demandKind ovGlobal matches 4 run function overlord:demand/measure_sacrifice
# (measure_survive may resolve the demand on a death; gate the rest on still-active)
execute if score #demandActive ovGlobal matches 1 run function overlord:demand/update_bar
execute if score #demandActive ovGlobal matches 1 run function overlord:demand/phases
# progress-based success applies to score(0), altar(1), and sacrifice(4); not to
# freeform(2) or survive(3), which resolve only by judgement or by reaching the end.
execute if score #demandActive ovGlobal matches 1 if score #demandKind ovGlobal matches 0..1 if score #demandProg ovGlobal >= #demandThreshold ovGlobal run function overlord:demand/succeed
execute if score #demandActive ovGlobal matches 1 if score #demandKind ovGlobal matches 4 if score #demandProg ovGlobal >= #demandThreshold ovGlobal run function overlord:demand/succeed
execute if score #demandActive ovGlobal matches 1 if score #demandTimer ovGlobal matches ..0 run function overlord:demand/deadline
