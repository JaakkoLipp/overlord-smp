# One second of an active surge: count down, beat the cadence, spawn on the beat.
scoreboard players remove #surgeTimer ovGlobal 1
scoreboard players add #surgeBeat ovGlobal 1
execute if score #surgeBeat ovGlobal >= #surgeCadence ovGlobal run function overlord:wrath/surge_beat
