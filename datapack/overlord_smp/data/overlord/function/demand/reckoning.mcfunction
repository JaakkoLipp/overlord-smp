execute if score #demandPhase ovGlobal matches ..2 run function overlord:demand/enter_reckoning
execute if score #demandPhase ovGlobal matches 3 run scoreboard players remove #demandOvertime ovGlobal 1
execute if score #demandPhase ovGlobal matches 3 if score #demandOvertime ovGlobal matches ..0 run function overlord:demand/fail
