# macro arg r = link radius. Recipients within r of the source position.
$execute store result score #k ovTmp if entity @a[tag=!ov_self,tag=!ov_dead,distance=..$(r)]
