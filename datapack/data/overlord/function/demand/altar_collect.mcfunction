$execute as @e[type=item,distance=..3,nbt={Item:{id:"$(item)"}}] run function overlord:demand/count_one
$kill @e[type=item,distance=..3,nbt={Item:{id:"$(item)"}}]
