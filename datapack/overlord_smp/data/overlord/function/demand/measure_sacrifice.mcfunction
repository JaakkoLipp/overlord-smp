# source 0 = altar: tally + consume weighted valuables delivered to any altar.
# source 1 = pool : progress is FRESH favor added since the demand began (pool minus the
#                   snapshot), spent on success. Clamped at 0 if the pool is drawn down.
execute if score #sacSource ovGlobal matches 0 run function overlord:demand/sacrifice_collect
execute if score #sacSource ovGlobal matches 1 run scoreboard players operation #demandProg ovGlobal = #favorPool ovGlobal
execute if score #sacSource ovGlobal matches 1 run scoreboard players operation #demandProg ovGlobal -= #favorPoolBase ovGlobal
execute if score #sacSource ovGlobal matches 1 if score #demandProg ovGlobal matches ..-1 run scoreboard players set #demandProg ovGlobal 0
