# freeform -> model judges; survive -> reaching the end IS the win; score/altar/
# sacrifice -> a Reckoning overtime to claw it back.
execute if score #demandKind ovGlobal matches 2 run function overlord:demand/judge_request
execute if score #demandKind ovGlobal matches 3 run function overlord:demand/succeed
execute if score #demandKind ovGlobal matches 0..1 run function overlord:demand/reckoning
execute if score #demandKind ovGlobal matches 4 run function overlord:demand/reckoning
