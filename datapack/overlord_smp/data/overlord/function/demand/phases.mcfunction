execute if score #demandPhase ovGlobal matches 0 if score #demandTimer ovGlobal <= #demandHalf ovGlobal run function overlord:demand/enter_half
execute if score #demandPhase ovGlobal matches 1 if score #demandTimer ovGlobal <= #demandQuarter ovGlobal run function overlord:demand/enter_quarter
