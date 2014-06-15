from collections import OrderedDict
try:
	import xml.etree.cElementTree as ET
except ImportError:
	import xml.etree.ElementTree as ET

from rooms import Room, Exit


class Database(object):
	"""Pandora database class"""
	directionNames = OrderedDict([
		("n", "north"),
		("s", "south"),
		("e", "east"),
		("w", "west"),
		("u", "up"),
		("d", "down")])

	def getElements(self, fileName, tag):
		"""returns an iterater of all the tags matching tag from the xml file in fileName"""
		context = iter(ET.iterparse(fileName, events=("start", "end")))
		event, root = next(context)
		for event, element in context:
			if event=="end" and element.tag==tag:
				yield element
				# Free up the memory used.
				root.clear()

	def __init__(self, fileName):
		# iterate through the rooms in the database, creating an object for each room.
		self.rooms = {}
		for element in self.getElements(fileName, "room"):
			obj = Room()
			obj.id = element.get("id")
			obj.x = element.get("x")
			obj.y = element.get("y")
			obj.z = element.get("z")
			obj.region = element.get("region")
			obj.terrain = element.get("terrain", "UNDEFINED")
			obj.name = element.findtext("roomname")
			obj.desc = element.findtext("desc")
			obj.note = element.findtext("note")
			obj.exits = []
			for x in element.findall("./exits/exit"):
				newExit = Exit()
				newExit.dir = self.directionNames[x.get("dir")]
				newExit.to = x.get("to")
				newExit.door = x.get("door")
				obj.exits.append(newExit)
			obj.exits.sort(key=lambda k:self.directionNames.values().index(k.dir))
			obj.setCost(obj.terrain)
			# Add a reference to the room object to our self.rooms dict, using the room ID as the key.
			self.rooms[obj.id] = obj
