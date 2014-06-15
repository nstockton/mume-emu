TERRAINS = {
	# Name: (Symbol for prompt, Cost for path Find)
	"INDOORS": ("[", 1.0),
	"CITY": ("#", 1.0),
	"ROAD": ("+", 1.1),
	"FIELD": (".", 1.2),
	"CAVERN": ("O", 1.2),
	"TUNNEL": ("=", 1.2),
	"SHALLOWWATER": ("%", 1.3),
	"FOREST": ("f", 1.4),
	"HILLS": ("(", 2.0),
	"BRUSH": (":", 2.5),
	"MOUNTAINS": ("<", 3.0),
	"UNDEFINED": ("", 5.0),
	"WATER": ("~", 15.0),
	"RAPIDS": ("W", 25.0),
	"UNDERWATER": ("U", 30.0),
	"RANDOM": ("|", 90.0),
	"DEATH": ("?", 100.0)}


class Room(object):
	"""A class representing a room in the world"""

	def setCost(self, value):
		self.terrainSymbol, self.cost = TERRAINS.get(value, ("", 5.0))


class Exit(object):
	pass
