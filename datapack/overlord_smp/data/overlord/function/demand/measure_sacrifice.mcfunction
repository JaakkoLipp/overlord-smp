# source 0 = altar: tally + consume weighted valuables delivered to any altar.
# source 1 = pool : progress mirrors the communal favor pool (spent on success).
execute if score #sacSource ovGlobal matches 0 run function overlord:demand/sacrifice_collect
execute if score #sacSource ovGlobal matches 1 run scoreboard players operation #demandProg ovGlobal = #favorPool ovGlobal
