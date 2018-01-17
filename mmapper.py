# This module was originally written by Chris Brannon.
# https://github.com/CMB
# Chris has graciously placed the source code of this module in the public domain.

import cStringIO
import struct
import zlib

from jd2gcal import jd2gcal
from rooms import Room, Exit


MMAPPER_MAGIC = 0xffb2af01
MMAPPER_VERSIONS = (031, 040, 041, 042)
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
		self.marks = []


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
	("no_match", 7),
	("flow", 8),
	("no_flee", 9)
])

doorflags = NamedBitFlags([
	("hidden", 1),
	("needkey", 2),
	("noblock", 3),
	("nobreak", 4),
	("nopick", 5),
	("delayed", 6),
	("callable", 7),
	("knockable", 8),
	("magic", 9),
	("action", 10)
])

align_type = {
	0: "undefined",
	1: "good",
	2: "neutral",
	3: "evil"}

info_mark_type = {
	0: "text",
	1: "line",
	2: "arrow"
}

info_mark_class = {
	0: "generic",
	1: "herb",
	2: "river",
	3: "place",
	4: "mob",
	5: "comment",
	6: "road",
	7: "object",
	8: "action",
	9: "locality"
}

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

sundeath_type = {
	0: "undefined",
	1: "sundeath",
	2: "nosundeath"}

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


def read_exit(version, infileobj):
	new_exit = Exit()
	if version >= 041:
		new_exit.exitFlags = exitflags.bits_to_flag_set(read_uint16(infileobj))
	else:
		new_exit.exitFlags = exitflags.bits_to_flag_set(read_uint8(infileobj))
	if version >= 040:
		new_exit.doorFlags = doorflags.bits_to_flag_set(read_uint16(infileobj))
	else:
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


def read_exits(version, infileobj):
	exits = []
	exit_names = ["north", "south", "east", "west", "up", "down", "unknown"]
	for exit_name in exit_names:
		new_exit = read_exit(version, infileobj)
		if new_exit.exitFlags:
			new_exit.dir = exit_name
			exits.append(new_exit)
	return exits


def read_room(version, infileobj):
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
	if version >= 030:
		new_room.ridable = ridable_type[read_uint8(infileobj)]
	if version >= 041:
		new_room.sundeath = sundeath_type[read_uint8(infileobj)]
		new_room.mobFlags = mobflags.bits_to_flag_set(read_uint32(infileobj))
		new_room.loadFlags = loadflags.bits_to_flag_set(read_uint32(infileobj))
	else:
		new_room.mobFlags = mobflags.bits_to_flag_set(read_uint16(infileobj))
		new_room.loadFlags = loadflags.bits_to_flag_set(read_uint16(infileobj))
	new_room.updated = bool(read_uint8(infileobj))
	new_room.x = read_int32(infileobj)
	new_room.y = read_int32(infileobj)
	new_room.z = read_int32(infileobj)
	new_room.exits = read_exits(version, infileobj) #[x for x in read_exits(version, infileobj)]
	return new_room


class InfoMark(object):
	type = "text"
	cls = "generic"
	rotation_angle = 0.0


def read_mark(version, infileobj):
	mark = InfoMark()
	mark.name = read_qstring(infileobj)
	mark.text = read_qstring(infileobj)
	jd = read_uint32(infileobj) # Julian day number
	if jd == 0:
		# QDate objects don't have a year 0.
		jd = None
	ms = read_uint32(infileobj) # Milliseconds since midnight
	if ms == UINT_MAX:
		ms = None
	tz = read_uint8(infileobj) # 0 = local time, 1 = UTC
	if tz == 0xff:
		tz = None
	mark.time_stamp = jd2gcal(jd, ms, tz)
	mark.type = info_mark_type[read_uint8(infileobj)]
	if version >= 040:
		mark.cls = info_mark_class[read_uint8(infileobj)]
		mark.rotation_angle = read_uint32(infileobj) / 100.0
	mark.pos1 = {
		"x": read_int32(infileobj) / 100.0,
		"y": read_int32(infileobj) / 100.0,
		"z": read_int32(infileobj)
	}
	mark.pos2 = {
		"x": read_int32(infileobj) / 100.0,
		"y": read_int32(infileobj) / 100.0,
		"z": read_int32(infileobj)
	}
	return mark


def decompress_mmapper_data(version, infileobj):
	if version >= 042:
		# As of version 042 of the MMapper data format, MMapper uses qCompress and qUncompress from the QByteArray class for data compression.
		# From the web page at
		# https://doc.qt.io/archives/qt-5.7/qbytearray.html#qUncompress
		# "Note: If you want to use this function to uncompress external data that was compressed using zlib, you first need to prepend a four byte header to the byte array containing the data. The header must contain the expected length (in bytes) of the uncompressed data, expressed as an unsigned, big-endian, 32-bit integer."
		# We can therefore assume that MMapper data files with version 042 or later are compressed using standard zlib with a non-standard 4-byte header.
		header = read_uint32(infileobj)
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
		version = read_int32(infileobj)
		if version not in MMAPPER_VERSIONS:
			raise UnsupportedVersionException(version)
		decompressed_stream = decompress_mmapper_data(version, infileobj)
	data = MMapperData()
	data.version = version
	rooms_count = read_uint32(decompressed_stream)
	marks_count = read_uint32(decompressed_stream)
	data.selected = (read_int32(decompressed_stream), read_int32(decompressed_stream), read_int32(decompressed_stream))
	for i in xrange(rooms_count):
		room = read_room(version, decompressed_stream)
		data.rooms[room.id] = room
	if version >= 042:
		# Reading marks are broken in V042 of the database format. Will need to look into this.
		return data
	for i in xrange(marks_count):
		data.marks.append(read_mark(version, decompressed_stream))
		# Do we want the marks?  How do they work, exactly?
	return data


class Database(object):
	"""MMapper database class"""

	def __init__(self, fileName):
		with open(fileName, 'rb') as infileobj:
			num = read_uint32(infileobj)
			if num != MMAPPER_MAGIC:
				raise BadMagicNumberException()
			version = read_int32(infileobj)
			if version not in MMAPPER_VERSIONS:
				raise UnsupportedVersionException(version)
			decompressedStream = decompress_mmapper_data(version, infileobj)
		roomsCount = read_uint32(decompressedStream)
		marksCount = read_uint32(decompressedStream)
		self.selected = (read_int32(decompressedStream), read_int32(decompressedStream), read_int32(decompressedStream))
		# iterate through the rooms in the database, creating an object for each room.
		deathIDs = []
		self.rooms = {}
		for i in xrange(roomsCount):
			newRoom = read_room(version, decompressedStream)
			if newRoom.terrain == "DEATH":
				deathIDs.append(newRoom.id)
			else:
				newRoom.setCost(newRoom.terrain)
				self.rooms[newRoom.id] = newRoom
		for roomID, room in self.rooms.iteritems():
			for item in room.exits:
				if item.to in deathIDs:
					item.to = "DEATH"
