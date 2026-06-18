scoreboard players operation #t ovTmp = @s ovDemand
scoreboard players operation #t ovTmp -= @s ovDemandBase
execute if score #t ovTmp matches ..-1 run scoreboard players set #t ovTmp 0
scoreboard players operation #demandProg ovGlobal += #t ovTmp
