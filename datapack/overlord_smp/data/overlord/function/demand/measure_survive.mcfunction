# Per second of a survive ordeal: refresh the vitals bar, fail instantly if anyone
# has died since baseline, otherwise ramp the threat as the clock runs down.
function overlord:demand/vitals
execute if score #deathTally ovGlobal > #surviveBaseDeaths ovGlobal run function overlord:demand/survive_fail
execute if score #demandActive ovGlobal matches 1 run function overlord:demand/survive_ramp
