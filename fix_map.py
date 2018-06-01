#!/usr/bin/env python

# Code adapted from the module at https://github.com/nstockton/mume-emu/blob/master/mmapper.py
# Original module written by Chris Brannon (https://github.com/CMB).
# With modifications and updates by Nick Stockton (https://github.com/nstockton).

# This code is dedicated to the public domain. Do with it what you will.


from __future__ import print_function

import argparse
import io
import struct
import zlib

UINT8_MAX = 0xff
UINT32_MAX = 0xffffffff
MMAPPER_MAGIC = 0xffb2af01
MMAPPER_VERSIONS = (0o31, 0o40, 0o41, 0o42)

# For Python 3 compatibility.
try:
	xrange
except NameError:
	xrange = range


class MMapperException(Exception):
	pass


class IncompleteDataFileException(MMapperException):
	pass


class BadMagicNumberException(MMapperException):
	pass


class UnsupportedVersionException(MMapperException):
	def __init__(self, number):
		MMapperException.__init__(self, "Do not support version 0{:o} of mmapper data".format(number))


def read_uint32(infileobj):
	data = infileobj.read(4)
	if len(data) != 4:
		raise IncompleteDataFileException()
	return data


def read_int32(infileobj):
	data = infileobj.read(4)
	if len(data) != 4:
		raise IncompleteDataFileException()
	return data


def read_uint16(infileobj):
	data = infileobj.read(2)
	if len(data) != 2:
		raise IncompleteDataFileException()
	return data


def read_int16(infileobj):
	data = infileobj.read(2)
	if len(data) != 2:
		raise IncompleteDataFileException()
	return data


def read_uint8(infileobj):
	data = infileobj.read(1)
	if len(data) != 1:
		raise IncompleteDataFileException()
	return data


def read_int8(infileobj):
	data = infileobj.read(1)
	if len(data) != 1:
		raise IncompleteDataFileException()
	return data


def read_qstring(infileobj):
	length = read_uint32(infileobj)
	unpacked_length = struct.unpack(">I", length)[0]
	if unpacked_length == UINT32_MAX:
		return length
	ucs_data = infileobj.read(unpacked_length)
	if len(ucs_data) != unpacked_length:
		raise IncompleteDataFileException()
	return length + ucs_data


def decompress_mmapper_data(infileobj, version):
	if version >= 0o42:
		# As of version 042 of the MMapper data format, MMapper uses qCompress and qUncompress from the QByteArray class for data compression.
		# From the web page at
		# https://doc.qt.io/archives/qt-5.7/qbytearray.html#qUncompress
		# "Note: If you want to use this function to uncompress external data that was compressed using zlib, you first need to prepend a four byte header to the byte array containing the data. The header must contain the expected length (in bytes) of the uncompressed data, expressed as an unsigned, big-endian, 32-bit integer."
		# We can therefore assume that MMapper data files with version 042 or later are compressed using standard zlib with a non-standard 4-byte header.
		header = read_uint32(infileobj)
	BLOCK_SIZE = 8192
	decompressor = zlib.decompressobj()
	decompressed_stream = io.BytesIO()
	compressed_data = infileobj.read(BLOCK_SIZE)
	while compressed_data:
		decompressed_stream.write(decompressor.decompress(compressed_data))
		compressed_data = infileobj.read(BLOCK_SIZE)
	decompressed_stream.seek(0)
	return decompressed_stream


def read_room(infileobj, outfileobj, version):
	outfileobj.write(read_qstring(infileobj)) # room name
	outfileobj.write(read_qstring(infileobj)) # room static description
	outfileobj.write(read_qstring(infileobj)) # room dynamic description
	outfileobj.write(read_uint32(infileobj)) # room ID
	outfileobj.write(read_qstring(infileobj)) # room note
	outfileobj.write(read_uint8(infileobj)) # room terrain
	outfileobj.write(read_uint8(infileobj)) # room light
	outfileobj.write(read_uint8(infileobj)) # room alignment
	outfileobj.write(read_uint8(infileobj)) # room portable
	outfileobj.write(read_uint8(infileobj)) # room ridable
	if version >= 0o41:
		outfileobj.write(read_uint8(infileobj)) # room sun death
		outfileobj.write(read_uint32(infileobj)) # room mob flags
		outfileobj.write(read_uint32(infileobj)) # room load flags
	else:
		outfileobj.write(struct.pack("B", 0)) # room sun death (undefined)
		mob_flags = struct.unpack(">H", read_uint16(infileobj))[0]
		outfileobj.write(struct.pack(">I", mob_flags)) # room mob flags (converted to uint32)
		load_flags = struct.unpack(">H", read_uint16(infileobj))[0]
		outfileobj.write(struct.pack(">I", load_flags)) # room load flags (converted to uint32)
	outfileobj.write(read_uint8(infileobj)) # room updated
	outfileobj.write(read_int32(infileobj)) # room X
	outfileobj.write(read_int32(infileobj)) # room Y
	outfileobj.write(read_int32(infileobj)) # room Z
	for exit_name in ("north", "south", "east", "west", "up", "down", "unknown"):
		if version >= 0o41:
			outfileobj.write(read_uint16(infileobj)) # exit flags
		else:
			exit_flags = struct.unpack("B", read_uint8(infileobj))[0]
			outfileobj.write(struct.pack(">H", exit_flags)) # exit flags (converted to uint16)
		if version >= 0o40:
			outfileobj.write(read_uint16(infileobj)) # door flags
		else:
			door_flags = struct.unpack("B", read_uint8(infileobj))[0]
			outfileobj.write(struct.pack(">H", door_flags)) # door flags (converted to uint16)
		outfileobj.write(read_qstring(infileobj)) # door name
		connection = read_uint32(infileobj) # first inbound connection
		outfileobj.write(connection)
		while struct.unpack(">I", connection)[0] != UINT32_MAX:
			connection = read_uint32(infileobj) # inbound connections
			outfileobj.write(connection)
		connection = read_uint32(infileobj) # first outbound connection
		outfileobj.write(connection)
		while struct.unpack(">I", connection)[0] != UINT32_MAX:
			connection = read_uint32(infileobj) # outbound connections
			outfileobj.write(connection)


def read_mark(infileobj, outfileobj, version):
	outfileobj.write(read_qstring(infileobj)) # mark name
	outfileobj.write(read_qstring(infileobj)) # mark text
	outfileobj.write(read_uint32(infileobj)) # mark Julian day
	outfileobj.write(read_uint32(infileobj)) # mark milliseconds since midnight
	outfileobj.write(read_uint8(infileobj)) # mark time zone 0 = local time, 1 = UTC
	outfileobj.write(read_uint8(infileobj)) # mark type
	if version >= 0o40:
		outfileobj.write(read_uint8(infileobj)) # mark class
		outfileobj.write(read_uint32(infileobj)) # mark rotation angle
	else:
		outfileobj.write(struct.pack("B", 0)) # mark class (generic)
		outfileobj.write(struct.pack(">I", 0.0)) # mark rotation angle (0.0)
	outfileobj.write(read_int32(infileobj)) # pos1 X
	outfileobj.write(read_int32(infileobj)) # pos1 Y
	outfileobj.write(read_int32(infileobj)) # pos1 Z
	outfileobj.write(read_int32(infileobj)) # pos2 X
	outfileobj.write(read_int32(infileobj)) # pos2 Y
	outfileobj.write(read_int32(infileobj)) # pos2 Z


def fix_map(corrupted_file, previous_file, output_file):
	print("Decompressing corrupted database ({name}).".format(name=corrupted_file))
	with open(corrupted_file, "rb") as infileobj:
		num = read_uint32(infileobj)
		if struct.unpack(">I", num)[0] != MMAPPER_MAGIC:
			raise BadMagicNumberException()
		version = read_int32(infileobj)
		unpacked_version = struct.unpack(">i", version)[0]
		if unpacked_version not in MMAPPER_VERSIONS:
			raise UnsupportedVersionException(unpacked_version)
		decompressed_stream = decompress_mmapper_data(infileobj, unpacked_version)
	print("Extracting rooms. These will be used.")
	rooms_count = read_uint32(decompressed_stream)
	marks_count = read_uint32(decompressed_stream)
	output_stream = io.BytesIO()
	output_stream.write(rooms_count)
	output_stream.write(marks_count)
	output_stream.write(read_int32(decompressed_stream)) # selected X
	output_stream.write(read_int32(decompressed_stream)) # selected Y
	output_stream.write(read_int32(decompressed_stream)) # selected Z
	for i in xrange(struct.unpack(">I", rooms_count)[0]):
		read_room(decompressed_stream, output_stream, unpacked_version)
	# Free up the memory
	decompressed_stream.seek(0)
	decompressed_stream.truncate()
	decompressed_stream.close()
	del decompressed_stream
	print("Decompressing previous database ({name}).".format(name=previous_file))
	with open(previous_file, "rb") as infileobj:
		num = read_uint32(infileobj)
		if struct.unpack(">I", num)[0] != MMAPPER_MAGIC:
			raise BadMagicNumberException()
		version = read_int32(infileobj)
		unpacked_version = struct.unpack(">i", version)[0]
		if unpacked_version not in MMAPPER_VERSIONS:
			raise UnsupportedVersionException(unpacked_version)
		decompressed_stream = decompress_mmapper_data(infileobj, unpacked_version)
	print("Extracting rooms. These will *not* be used.")
	rooms_count = read_uint32(decompressed_stream)
	marks_count = read_uint32(decompressed_stream)
	# overwrite marks_count in the output stream with the new value
	output_stream.seek(4)
	output_stream.write(marks_count)
	# seek to the end of the stream.
	output_stream.seek(0, 2)
	read_int32(decompressed_stream) # selected X
	read_int32(decompressed_stream) # selected Y
	read_int32(decompressed_stream) # selected Z
	junk_stream = io.BytesIO()
	for i in xrange(struct.unpack(">I", rooms_count)[0]):
		read_room(decompressed_stream, junk_stream, unpacked_version)
		junk_stream.seek(0)
		junk_stream.truncate()
	junk_stream.close()
	del junk_stream
	print("Extracting info marks. These will be used.")
	for i in xrange(struct.unpack(">I", marks_count)[0]):
		read_mark(decompressed_stream, output_stream, unpacked_version)
	# Free up the memory
	decompressed_stream.seek(0)
	decompressed_stream.truncate()
	decompressed_stream.close()
	del decompressed_stream
	print("Compressing and saving output database ({name}).".format(name=output_file))
	output_header = output_stream.tell() # the length of the uncompressed data, required for database V042,
	output_stream.seek(0)
	BLOCK_SIZE = 8192
	with open(output_file, "wb") as outfileobj:
		outfileobj.write(struct.pack(">I", MMAPPER_MAGIC)) # MMapper Magic (uint32)
		outfileobj.write(struct.pack(">i", 0o42)) # database version (int32)
		outfileobj.write(struct.pack(">I", output_header)) # The size in bytes of data *before* compression (uint32)
		compressor = zlib.compressobj()
		uncompressed_data = output_stream.read(BLOCK_SIZE)
		while uncompressed_data:
			outfileobj.write(compressor.compress(uncompressed_data))
			uncompressed_data = output_stream.read(BLOCK_SIZE)
		outfileobj.write(compressor.flush())
	print("Done.")


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Replace corrupted info marks from saved MMapper V2.4.3 maps with the info marks from a pre-2.4.3 map.")
	parser.add_argument("-c", "--corrupted", help="The MMapper V2.4.3 database file with *corrupted* info marks. Only room data will be used from this file.", action="store", required=True)
	parser.add_argument("-p", "--previous", help="The *previous* (MMapper V2.4.2 or lower) database file to extract info marks from. Only info marks will be used from this file.", action="store", required=True)
	parser.add_argument("-o", "--output", help="The name of the output file. The output will be version 042 format, compatible with MMapper V2.4.4.", action="store", required=True)
	args = parser.parse_args()
	fix_map(args.corrupted, args.previous, args.output)
