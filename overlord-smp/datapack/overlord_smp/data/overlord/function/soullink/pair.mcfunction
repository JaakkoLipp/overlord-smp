# macro arg: pair = tag identifying the two bonded players
$execute as @a[tag=$(pair)] run function overlord:soullink/member {pair:"$(pair)"}
