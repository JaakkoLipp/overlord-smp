$execute as @a[tag=!ov_self,tag=!ov_dead,distance=..$(r)] run scoreboard players operation @s ovDmgPrev += #adj ovTmp
$execute as @a[tag=!ov_self,tag=!ov_dead,distance=..$(r)] run damage @s $(amt) minecraft:magic
