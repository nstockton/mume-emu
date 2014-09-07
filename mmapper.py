# This module was originally written by Chris Brannon.
# https://github.com/CMB
# Chris has graciously placed the source code of this module in the public domain.

import cStringIO
import struct
import zlib

from rooms import Room, Exit


MMAPPER_MAGIC = 0xffb2af01
MMAPPER_VERSION = 031
UINT_MAX = 0xffffffff


class MMapperException(Exception):
	pass


class IncompleteDataFileException(MMapperException):
	pass


class BadMagicNumberException(MMapperException):
	pass


class UnsupportedVersionException(MMapperException):
	def __init__(self, number):
		MMapperException.__init__(self, "Do not support version %d of mmapper data" % number)


class NamedBitFlags(object):
	def __init__(self, names_and_bits):
		self.map_by_name = {}
		self.map_by_number = {}
		for name, bit in names_and_bits:
			self.map_by_number[1 << (bit - 1)] = name
			self.map_by_name[name] = 1 << (bit - 1)

	def bits_to_flag_set(self, bits):
		flag_set = set()
		for num in self.map_by_number.keys():
			if bits & num:
				flag_set.add(self.map_by_number[num])
		return flag_set


# Need to clean up these classes later.
# There's no encapsulation here at all.
class MMapperData(object):
	# Fields: rooms, selected (a position)
	def __init__(self):
		self.rooms = {}


mobflags = NamedBitFlags([
	("rent", 1),
	("shop", 2),
	("weaponshop", 3),
	("armourshop", 4),
	("foodshop", 5),
	("petshop", 6),
	("guild", 7),
	("scoutguild", 8),
	("mageguild", 9),
	("clericguild", 10),
	("warriorguild", 11),
	("rangerguild", 12),
	("smob", 13),
	("quest", 14),
	("any", 15),
	("reserved2", 16)])

loadflags = NamedBitFlags([
	("treasure", 1),
	("armour", 2),
	("weapon", 3),
	("water", 4),
	("food", 5),
	("herb", 6),
	("key", 7),
	("mule", 8),
	("horse", 9),
	("packhorse", 10),
	("trainedhorse", 11),
	("rohirrim", 12),
	("warg", 13),
	("boat", 14),
	("attention", 15),
	("tower", 16)])

exitflags = NamedBitFlags([
	("exit", 1),
	("door", 2),
	("road", 3),
	("climb", 4),
	("random", 5),
	("special", 6),
	("no_match", 7)])

doorflags = NamedBitFlags([
	("hidden", 1),
	("needkey", 2),
	("noblock", 3),
	("nobreak", 4),
	("nopick", 5),
	("delayed", 6),
	("reserved1", 7),
	("reserved2", 8)])

align_type = {
	0: "undefined",
	1: "good",
	2: "neutral",
	3: "evil"}

light_type = {
	0: "undefined",
	1: "dark",
	2: "lit"}

portable_type = {
	0: "undefined",
	1: "portable",
	2: "notportable"}

ridable_type = {
	0: "undefined",
	1: "ridable",
	2: "notridable"}

terrain_type = {
	0: "UNDEFINED",
	1: "INDOORS",
	2: "CITY",
	3: "FIELD",
	4: "FOREST",
	5: "HILLS",
	6: "MOUNTAINS",
	7: "SHALLOWWATER",
	8: "WATER",
	9: "RAPIDS",
	10: "UNDERWATER",
	11: "ROAD",
	12: "BRUSH",
	13: "TUNNEL",
	14: "CAVERN",
	15: "DEATH",
	16: "RANDOM"}


def read_uint32(infileobj):
	data = infileobj.read(4)
	if len(data) != 4:
		raise IncompleteDataFileException()
	return struct.unpack(">I", data)[0]


def read_int32(infileobj):
	data = infileobj.read(4)
	if len(data) != 4:
		raise IncompleteDataFileException()
	return struct.unpack(">i", data)[0]


def read_uint16(infileobj):
	data = infileobj.read(2)
	if len(data) != 2:
		raise IncompleteDataFileException()
	return struct.unpack(">H", data)[0]


def read_int16(infileobj):
	data = infileobj.read(2)
	if len(data) != 2:
		raise IncompleteDataFileException()
	return struct.unpack(">h", data)[0]


def read_uint8(infileobj):
	data = infileobj.read(1)
	if len(data) != 1:
		raise IncompleteDataFileException()
	return struct.unpack("B", data)[0]


def read_int8(infileobj):
	data = infileobj.read(1)
	if len(data) != 1:
		raise IncompleteDataFileException()
	return struct.unpack("b", data)[0]


def read_qstring(infileobj):
	length = read_uint32(infileobj)
	if length == UINT_MAX:
		return ""
	ucs_data = infileobj.read(length)
	if len(ucs_data) != length:
		raise IncompleteDataFileException()
	return ucs_data.decode("UTF_16_BE")


def read_exit(infileobj):
	new_exit = Exit()
	new_exit.exitFlags = exitflags.bits_to_flag_set(read_uint8(infileobj))
	new_exit.doorFlags = doorflags.bits_to_flag_set(read_uint8(infileobj))
	new_exit.door = read_qstring(infileobj)
	if "door" in new_exit.exitFlags:
		new_exit.exitFlags.add("exit")
		if not new_exit.door:
			new_exit.door = "exit"
	# Inbound connections are unneeded.
	connection = read_uint32(infileobj)
	while connection != UINT_MAX:
		connection = read_uint32(infileobj)
	outConnections = []
	connection = read_uint32(infileobj)
	while connection != UINT_MAX:
		outConnections.append(str(connection))
		connection = read_uint32(infileobj)
	if not outConnections:
		new_exit.to = "UNDEFINED"
	else:
		# We want the last outbound connection.
		new_exit.to = outConnections[-1]
	return new_exit


def read_exits(infileobj):
	exits = []
	exit_names = ["north", "south", "east", "west", "up", "down", "unknown"]
	for exit_name in exit_names:
		new_exit = read_exit(infileobj)
		if new_exit.exitFlags:
			new_exit.dir = exit_name
			exits.append(new_exit)
	return exits


def read_room(infileobj):
	new_room = Room()
	new_room.name = read_qstring(infileobj)
	new_room.desc = read_qstring(infileobj)
	new_room.dynamicDesc = read_qstring(infileobj)
	new_room.id = str(read_uint32(infileobj))
	new_room.note = read_qstring(infileobj)
	new_room.terrain = terrain_type[read_uint8(infileobj)]
	new_room.light = light_type[read_uint8(infileobj)]
	new_room.align = align_type[read_uint8(infileobj)]
	new_room.portable = portable_type[read_uint8(infileobj)]
	new_room.ridable = ridable_type[read_uint8(infileobj)]
	new_room.mobFlags = mobflags.bits_to_flag_set(read_uint16(infileobj))
	new_room.loadFlags = loadflags.bits_to_flag_set(read_uint16(infileobj))
	new_room.updated = bool(read_uint8(infileobj))
	new_room.x = read_int32(infileobj)
	new_room.y = read_int32(infileobj)
	new_room.z = read_int32(infileobj)
	new_room.exits = read_exits(infileobj) #[x for x in read_exits(infileobj)]
	return new_room


def decompress_mmapper_data(infileobj):
	BLOCK_SIZE = 8192
	decompressor = zlib.decompressobj()
	decompressed_stream = cStringIO.StringIO()
	compressed_data = infileobj.read(BLOCK_SIZE)
	while compressed_data:
		decompressed_stream.write(decompressor.decompress(compressed_data))
		compressed_data = infileobj.read(BLOCK_SIZE)
	decompressed_stream.seek(0)
	return decompressed_stream


def read_mmapper_data(filename):
	with open(filename, "rb") as infileobj:
		num = read_uint32(infileobj)
		if num != MMAPPER_MAGIC:
			raise BadMagicNumberException()
		num = read_int32(infileobj)
		if num != MMAPPER_VERSION:
			raise UnsupportedVersionException(num)
		decompressed_stream = decompress_mmapper_data(infileobj)
	data = MMapperData()
	rooms_count = read_uint32(decompressed_stream)
	marks_count = read_uint32(decompressed_stream)
	data.selected = (read_int32(decompressed_stream), read_int32(decompressed_stream), read_int32(decompressed_stream))
	for i in xrange(rooms_count):
		room = read_room(decompressed_stream)
		data.rooms[room.id] = room
	#  for i in xrange(marks_count):
	#    data.mark_list.append(read_mark(decompressed_stream))
	# Do we want the marks?  How do they work, exactly?
	return data


class Database(object):
	"""MMapper database class"""

	def __init__(self, fileName):
		with open(fileName, 'rb') as infileobj:
			num = read_uint32(infileobj)
			if num != MMAPPER_MAGIC:
				raise BadMagicNumberException()
			num = read_int32(infileobj)
			if num != MMAPPER_VERSION:
				raise UnsupportedVersionException(num)
			decompressedStream = decompress_mmapper_data(infileobj)
		roomsCount = read_uint32(decompressedStream)
		marksCount = read_uint32(decompressedStream)
		self.selected = (read_int32(decompressedStream), read_int32(decompressedStream), read_int32(decompressedStream))
		# iterate through the rooms in the database, creating an object for each room.
		deathIDs = []
		self.rooms = {}
		for i in xrange(roomsCount):
			newRoom = read_room(decompressedStream)
			if newRoom.terrain == "DEATH":
				deathIDs.append(newRoom.id)
			else:
				newRoom.setCost(newRoom.terrain)
				self.rooms[newRoom.id] = newRoom
		for roomID, room in self.rooms.iteritems():
			for item in room.exits:
				if item.to in deathIDs:
					item.to = "DEATH"
