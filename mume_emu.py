#!/usr/bin/env python2

import argparse
import heapq
import itertools
import json
import re
import subprocess
import textwrap

import mmapper
import pandora
import terminalsize

ANSI_COLOR_REGEXP = re.compile(ur"[\n]?\x1b\[[0-9;]+[m][\n]?")


class World(object):
	"""The main world class"""
	width, height = terminalsize.get_terminal_size()

	def __init__(self, **kwargs):
		self.configFile = kwargs.get("configFile")
		# Load the configuration file.
		with open(self.configFile, "rb") as data:
			self.config = json.load(data, encoding="UTF-8")
		# Set up the labels dict inside the configuration if it isn't there.
		if "labels" not in self.config:
			self.config["labels"] = {}
		DB = kwargs.get("DBClass")
		self.rooms = DB(kwargs.get("databaseFile")).rooms
		# Set the initial room to the room that the user was in when the program last terminated.
		lastID = self.config.get("last_id")
		if lastID not in self.rooms:
			lastID = sorted(self.rooms.keys())[0]
		self.room = self.rooms[lastID]

	def filterAnsi(self, text):
		return ANSI_COLOR_REGEXP.sub('', text)

	def page(self, lines):
		if len(lines) < self.height:
			print "\n".join(lines)
		else:
			less = subprocess.Popen("less", stdin=subprocess.PIPE)
			less.stdin.write("\n".join(lines).encode("utf-8"))
			less.stdin.close()
			less.wait()

	def look(self):
		"""What to do when the user types 'look', enters a new room, ETC"""
		print self.filterAnsi(getattr(self.room, "name"))
		# If brief mode is disabled
		if not self.config.get("brief"):
			# In Pandora databases, The description text uses '|' (bar) as an end of line character. We need to replace these with '\n' new line characters before splitting the description by lines and doing our own word wrapping.
			desc = getattr(self.room, "desc", "").replace("|", "\n").splitlines()
			# Now we need to strip any whitespace characters from the description lines, as well as filtering out any blank lines.
			desc = [line.strip() for line in desc if line.strip()]
			# We need to word wrap the description to 1 less than the terminal width, or else we will occasionally see blank lines in the description.
			print self.filterAnsi(textwrap.fill(" ".join(desc), self.width-1))
		for line in self.filterAnsi(getattr(self.room, "dynamicDesc", "")).splitlines():
			if line:
				print textwrap.fill(line, self.width-1)
		#loop through the list of exits in the current room, and build the doors/exits lines.
		doorList = []
		exitList = []
		for item in getattr(self.room, "exits", []):
			direction = item.dir
			to = item.to
			door = item.door
			doorFlags = getattr(item, "doorFlags", ())
			# If there is a door in that direction
			if door:
				doorList.append("%s: %s" % (direction, door))
				# Doors with a name of 'exit' are not hidden exits in Mume. The actual door name in the game could be anything.
				if door == "exit" or "hidden" not in doorFlags:
					# Now that the direction has been added to the doors list, we will enclose it in parentheses '()' for use in the exits line. In Mume, enclosing an exits line direction in parentheses denotes an opened door in that direction.
					direction = "(%s)" % direction
				else:
					# The door is a secret exit.
					# Now that the direction and door names have been added to the doors list, we will enclose the direction in brackets '[]' for use in the exits line. In Mume, enclosing an exits line direction in brackets denotes a closed door in that direction.
					direction = "[%s]" % direction
			# The next 2 are just convenience symbols for denoting if the exit is to an undefined room or a known deathtrap.  They aren't used in Mume. The '=' signs are used in Mume to denote that the room in that direction is a road though.
			if to == "DEATH":
				direction = "!!%s!!" % direction
			elif to not in self.rooms or to=="UNDEFINED":
				direction = "??%s??" % direction
			elif getattr(self.rooms[to], "terrain") == "ROAD":
				direction = "=%s=" % direction
			# Now that we are done manipulating the direction string, we'll add it to the exits list.
			exitList.append(direction)
		# If any of the exits had a door, print the direction and name of the door if applicable.
		if doorList:
			print "Doors:"
			print ",\n".join(doorList)
		# print the exits line
		if not exitList:
			exitList.append("None!")
		print "Exits: %s" % ", ".join(exitList)
		note = getattr(self.room, "note", "").strip()
		if note:
			print "Note: %s" % self.filterAnsi(note)
		# If the user has enabled the showing of room IDs in the configuration, print the room ID.
		if self.config.get("show_id"):
			print "ID: %s" % getattr(self.room, "id", "NONE")

	def longExits(self):
		"""The exits command"""
		print "Exits:"
		roomExits = getattr(self.room, "exits", [])
		if not roomExits:
			print "None!"
			return
		for item in roomExits:
			exitLine = []
			exitLine.append("%s:" % item.dir.capitalize())
			door = item.door
			doorFlags = getattr(item, "doorFlags", ())
			if door:
				exitLine.append("%s (%s)," % ("visible" if door=="exit" or "hidden" not in doorFlags else "hidden", door))
			to = item.to
			if to.isdigit() and to in self.rooms:
				exitLine.append("%s, %s" % (self.filterAnsi(getattr(self.rooms[to], "name", "")), getattr(self.rooms[to], "terrain", "")))
			else:
				exitLine.append("UNDEFINED" if to!="DEATH" else to)
			print " ".join(exitLine)

	def setRoom(self, roomID):
		"""Sets the reference to the current room to the room object with roomID"""
		# UNDEFINED and DEATH aren't actual rooms in the database, they are just attributes of an exit.  We will therefore return "UNDEFINED" or "DEATH"
		if roomID=="UNDEFINED" or roomID=="DEATH":
			return roomID
		elif roomID not in self.rooms:
			return "UNDEFINED"
		self.room = self.rooms[roomID]
		self.config["last_id"] = roomID

	def toggleSetting(self, setting):
		"""This function handles configuration settings that can be toggled True/False"""
		# Toggle the value and return the new state
		self.config[setting] = self.config.get(setting, True) == False
		return self.config[setting]

	def saveConfig(self):
		"""Saves the configuration to disk"""
		with open(self.configFile, "wb") as data:
			json.dump(self.config, data, sort_keys=True, indent=2, separators=(",", ": "), encoding="UTF-8")

	def createSpeedWalk(self, directionsList):
		output = []
		for key, value in itertools.groupby(directionsList):
			lenValue = len(list(value))
			if lenValue == 1:
				output.append(key[0])
			else:
				output.append("{0}{1}".format(lenValue, key[0]))
		return "".join(output)

	def pathFind(self, origin=None, destination=None):
		"""Find the path"""
		if not origin or not destination:
			return "Error: Invalid origin or destination."
		elif origin == destination:
			return "You are already there!"
		# Each key-value pare that gets added to this dict will be a parent room and child room respectively.
		parents = {origin: origin}
		# unprocessed rooms.
		opened = []
		# Using a binary heap for storing unvisited rooms significantly increases performance.
		# https://en.wikipedia.org/wiki/Binary_heap
		heapq.heapify(opened)
		# Put the origin cost and origin room on the opened rooms heap to be processed first.
		heapq.heappush(opened, (origin.cost, origin))
		# previously processed rooms.
		closed = {}
		# Ignore the origin from the search by adding it to the closed rooms dict.
		closed[origin] = origin.cost
		# Search while there are rooms left in the opened heap.
		while opened:
			# Pop the last room cost and room object reference off the opened heap for processing.
			currentRoomCost, currentRoomObj = heapq.heappop(opened)
			if currentRoomObj == destination:
					# We successfully found a path from the origin to the destination.
					pathDirections = []
					# find the path from the origin to the destination by traversing the rooms that we passed through to get here.
					while currentRoomObj != origin:
						# Loop through the exits of the parent room, and find which exit links to the current room.
						for roomObj in parents[currentRoomObj].exits:
							if roomObj.to == currentRoomObj.id:
								# Insert the direction name at the beginning of the pathDirections list.
								pathDirections.insert(0, roomObj.dir)
								break
						# The parent room becomes the current room, and we repeat until all the parent rooms have been traversed.
						currentRoomObj = parents[currentRoomObj]
					# Return the directions in a standard speed walk format.
					return self.createSpeedWalk(pathDirections)
			# If we're here, the current room isn't the destination.
			# Loop through the exits, and process each room linked to the current room.
			for exitObj in currentRoomObj.exits:
				# Ignore exits that link to undefined or death trap rooms.
				if exitObj.to=="UNDEFINED" or exitObj.to=="DEATH" or exitObj.to not in self.rooms:
					continue
				# Get a reference to the room object that the exit leads to using the room's unique ID number.
				neighborRoomObj = self.rooms[exitObj.to]
				# The neighbor room cost should be the sum of all movement costs to get to the neighbor room from the origin room.
				neighborRoomCost = currentRoomCost + neighborRoomObj.cost
				# We're only interested in the neighbor room if it hasn't been encountered yet, or if the cost of moving from the current room to the neighbor room is less than the cost of moving to the neighbor room from a previously discovered room.
				if neighborRoomObj not in closed or closed[neighborRoomObj] > neighborRoomCost:
					# Add the room object and room cost to the dict of closed rooms, and put it on the opened rooms heap to be processed.
					closed[neighborRoomObj] = neighborRoomCost
					heapq.heappush(opened, (neighborRoomCost, neighborRoomObj))
					# Since the current room is so far the most optimal way into the neighbor room, set it as the parent of the neighbor room.
					parents[neighborRoomObj] = currentRoomObj
		# If we have made it this far, we've exhausted are search of all the connected rooms without finding the destination.
		return "No routes found."

	def labelRoom(self, label, target):
		"""Maps a 1-word, alphanumeric label to a room ID"""
		if target == "none":
			# If the target is 'none', delete the label if defined.
			try:
				self.config["labels"].pop(label)
			except KeyError:
				return "Error: No label with that name exists."
			self.saveConfig()
			return "Label %s removed." % label
		elif target in self.rooms:
			# create the label and save the configuration to disk
			self.config["labels"][label] = target
			self.saveConfig()
			return "label %s added for room ID %s." % (label, target)
		else:
			# The target wasn't a valid room ID in self.rooms
			return "Error: invalid room ID."

	def parseInput(self, line):
		"""Parses the user's input, and executes the appropriate command"""
		#split the line into words.
		args = line.split()
		# The first word is the command, and the rest of the words are possible arguments, so pop the first word from the list.
		command = args.pop(0)
		if command.isdigit():
			# User has typed in a possible room ID.  Move to the room with that ID if possible.
			status = self.setRoom(command)
			if status == "UNDEFINED":
				print "Invalid room ID."
			else:
				self.look()
		elif [x for x in getattr(self.room, "exits", []) if getattr(x, "dir", "UNDEFINED").startswith(command)]:
			# The user has typed in one of the exits from the current room's list of valid exits. Loop through the list of valid exits until we find the desired exit, and move to it.
			for item in getattr(self.room, "exits", []):
				if getattr(item, "dir", "UNDEFINED").startswith(command):
					status = self.setRoom(getattr(item, "to", "UNDEFINED"))
					if status == "UNDEFINED":
						print "Undefined room in that direction."
					elif status == "DEATH":
						print "Death trap in that direction."
					else:
						self.look()
					break
		elif "look".startswith(command):
			self.look()
		elif "id".startswith(command):
			status = self.toggleSetting("show_id")
			print "Show room ID %s." % ("enabled" if status else "disabled")
		elif "brief".startswith(command):
			status = self.toggleSetting("brief")
			print "Brief mode %s." % ("enabled" if status else "disabled")
		elif "terrain".startswith(command):
			status = self.toggleSetting("use_terrain_symbols")
			print "Terrain symbols in prompt %s." % ("enabled" if status else "disabled")
		elif command!="e" and "exits".startswith(command):
			self.longExits()
		elif "path".startswith(command):
			# This command takes 1 or 2 arguments
			if len(args) in [1, 2]:
				if args[-1] in self.config["labels"]:
					# The argument was a valid room label. Set the destination to the room object that has the ID in label.
					destination = self.rooms.get(self.config["labels"][args.pop()])
				else:
					# argument is a possible room ID. Try to set the destination to the room object with that ID.
					destination = self.rooms.get(args.pop())
				if not args:
					# An origin wasn't defined, so use the current room.
					origin = self.room
				elif args[0] in self.config["labels"]:
					# The argument was a valid room label. Set the origin to the room object that has the ID in label.
					origin = self.rooms.get(self.config["labels"][args.pop()])
				else:
					# argument is a possible room ID. Try to set the origin to the room object with that ID.
					origin = self.rooms.get(args.pop())
				print self.pathFind(origin, destination)
			else:
				print "Usage: path [origin] destination"
				print "Origin will default to the current room if not provided."
		elif "label".startswith(command):
			# This command takes 1 or 2 arguments
			if len(args) in [1, 2]:
				# The label is the first argument, the targeted room is the second if defined.
				label = args.pop(0)
				if label == "list":
					# print a sorted list of currently defined room labels.
					labelsList = ["%s: %s"%(key, value) for key, value in self.config["labels"].items()]
					labelsList.sort()
					labelsList.insert(0, "labels list:" if labelsList else "No labels defined yet.")
					self.page(labelsList)
				else:
					# If there is a second argument, apply the label to the room with that ID. Else, apply it to the current room.
					target = self.room.id if not args else args.pop()
					print self.labelRoom(label, target)
			else:
				print "Usage: label [list|[name [room_ID]"
				print "If room_ID is 'none', the label will be removed."
				print "Room_ID will default to the current room ID if not provided."
		elif command in self.config["labels"]:
			# The command was a valid room label.  Move to that room.
			self.setRoom(self.config["labels"][command])
			self.look()
		else:
			print "Invalid command or direction!"


def main():
	parser = argparse.ArgumentParser(description="Allows you to virtually explore the Mume world.")
	parser.add_argument("-c", "--config", help="the configuration file")
	group = parser.add_mutually_exclusive_group()
	group.add_argument("-m", "--mmapper", help="database is in MMapper 2 format", action="store_true")
	group.add_argument("-p", "--pandora", help="database is in Pandora Mapper format", action="store_true")
	parser.add_argument("databaseFile")
	args = parser.parse_args()
	if not args.config:
		print "You need to specify a configuration file."
		return
	if args.mmapper:
		DBClass = mmapper.Database
	elif args.pandora:
		DBClass = pandora.Database
	print "Welcome to Mume Map Emulation!"
	print "Loading the world database."
	world = World(configFile=args.config, DBClass=DBClass, databaseFile=args.databaseFile)
	print "Loaded %s rooms." % str(len(world.rooms))
	world.look()
	while True:
		# Indicate the current room's terrain in the prompt according to the setting of use_terrain_symbols in the configuration.
		prompt = "%s> " % (getattr(world.room, "terrainSymbol", "") if world.config.get("use_terrain_symbols") else getattr(world.room, "terrain", "UNDEFINED"))
		line = raw_input(prompt).strip().lower()
		if line:
			if "quit".startswith(line):
				# Break out of the loop, save the configuration to disk, and exit the program
				break
			world.parseInput(line)
	world.saveConfig()
	print "Good bye."


if __name__ == "__main__":
	main()
