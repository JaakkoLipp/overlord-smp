execute as @a[tag=!ov_self,tag=!ov_dead] run scoreboard players operation @s ovDmgPrev += #adj ovTmp
$execute as @a[tag=!ov_self,tag=!ov_dead] run damage @s $(amt) minecraft:magic
