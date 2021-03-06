"""
This PAC format is used in the PS2 game Legaia 2 Dual Saga and is simply multiple
files lumped together. The metadata is stored in little endian.The header starts
with 8 bytes that seem to be padding (always 0?), followed by the file count (4 bytes),
the PAC's total file size (4 bytes), and then a dictionary of file pointers (4 bytes)
paired with a 32 byte filepath. After that, the file content are dumped in one after
another.
"""

import struct, os, argparse

class Archive:
	def __init__(self):
		self.filenum = 0 # 4 bytes
		self.size = 16 # 4 bytes, initial value is 8 pad bytes, filenum, size
		self.filepos = [] # 4 bytes each
		self.filepaths = [] # 32 bytes each
	
	def log(self):
		print('Files: ', self.filenum, ' (', hex(self.filenum), ')')
		print('Size: ', self.size, ' (', hex(self.size), ')')
		print('File offsets: ', self.filepos)
		print('File paths: ', self.filepaths)
	
	def add(self, filepath):
		if os.path.exists(filepath):
			si = os.stat(filepath)
			self.filepos.append(self.size)
			self.filepaths.append(bytes(filepath, 'ascii'))
			self.size += (36 + si.st_size) # 36 = file offset + path
			self.filenum += 1
	
	def pack(self):
		# 8 pad bytes (?), file count, self size
		buf = struct.pack('<8xLL', self.filenum, self.size)

		# calculate offsets
		si = None
		pos = 0
		for k, v in enumerate(self.filepaths):
			if k == 0:
				# 16 = padding? (8) + file count (4) + pac size (4)
				# 36 = offset (4) + name length (32)
				self.filepos[k] = 16 + (36 * self.filenum)
				si = os.stat(v)
				pos = self.filepos[k] + si.st_size
			else:
				si = os.stat(v)
				self.filepos[k] = pos
				pos += si.st_size
		
		# file offset + path (32 char limit)
		for i in range(self.filenum):
			buf += struct.pack('<L32s', self.filepos[i], self.filepaths[i])
		
		# sequential file content dump
		for i in range(self.filenum):
			f = open(self.filepaths[i], 'r+b')
			buf += f.read()
			f.close()
		
		return buf
	
def unpack(buf):
	pos = 8 # after padding
	pac = Archive()
	
	# Unpack PAC metadata
	tmp = struct.unpack_from('<LL', buf, pos)
	pac.filenum = tmp[0] # tmp is always a tuple
	pac.size = tmp[1]
	pos += 8
	
	# Unpack file metadata
	for i in range(pac.filenum):
		tmp = struct.unpack_from('<L32s', buf, pos)
		pac.filepos.append(tmp[0])
		pac.filepaths.append(tmp[1])
		pos += 36
	
	# Unpack files
	for i in range(pac.filenum):
		s = str(pac.filepaths[i])[2:].replace('\\x00', '')
		s = s[:len(s)-1]
		nextpos = pos
		
		if ('/' in s) and (not os.path.exists(os.path.dirname(s))):
			os.makedirs(os.path.dirname(s))
		
		# last file in sequence?
		if i == (pac.filenum-1):
			tmp = open(s, 'w+b')
			tmp.write(buf[pos:])
			tmp.close()
		else:
			nextpos = pac.filepos[i+1]
			tmp = open(s, 'w+b')
			tmp.write(buf[pos:nextpos])
			tmp.close
		
		pos = nextpos

	return pac

def main():
	parser = argparse.ArgumentParser(description='PlayStation 2 PAC file utility')
	parser.add_argument('-x', metavar='PAC_archive', type=str, help='Extract files')
	parser.add_argument('-c', metavar='filename', type=str, nargs='+', help='Create PAC file')
	parser.add_argument('-o', metavar='filename', type=str, help='Output PAC name')
	args = parser.parse_args()
	
	if (args.c == None) and (args.x == None):
		parser.print_help()
	
	if (args.c != None) and (args.x != None):
		parser.print_help()
	
	if (args.c == None) and (args.x != None):
		f = open(args.x, 'r+b')
		unpack(f.read())
		f.close()
	
	if (args.c != None) and (args.x == None):
		p = Archive()
		for i in range(len(args.c)):
			p.add(args.c[i])
		f = open(args.o, 'w+b')
		f.write(p.pack())
		f.close()
		p.log()

if __name__ == '__main__':
	main()
