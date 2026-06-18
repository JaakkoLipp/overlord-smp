# context: @s = altar marker. A living player within 10 blocks may pay to revive.
execute as @p[distance=..10,tag=!ov_dead] run function overlord:revival/commit
