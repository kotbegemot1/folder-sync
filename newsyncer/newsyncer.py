import os
import sys
import shutil
import stat
import filecmp

from dirsync.syncer import Syncer
from loguru import logger



logger.remove()
logger.add('{}'.format(sys.argv[4]), format="{time} {level} {message}", level="INFO")

class NewSyncer(Syncer):
	def _copy(self, filename, dir1, dir2):
		""" Private function for copying a file """

		# NOTE: dir1 is source & dir2 is target
		if self._copyfiles:

			rel_path = filename.replace('\\', '/').split('/')
			rel_dir = '/'.join(rel_path[:-1])
			filename = rel_path[-1]

			dir2_root = dir2

			dir1 = os.path.join(dir1, rel_dir)
			dir2 = os.path.join(dir2, rel_dir)

			if self._verbose:
				logger.info("Копирование фала: {}\\{}".format(dir2, filename)) #запись о копировании в файл
				self.log('Copying file %s from %s to %s' %
						 (filename, dir1, dir2))
			try:
				# source to target
				if self._copydirection == 0 or self._copydirection == 2:

					if not os.path.exists(dir2):
						if self._forcecopy:
							# 1911 = 0o777
							os.chmod(os.path.dirname(dir2_root), 1911)
						try:
							os.makedirs(dir2)
							self._numnewdirs += 1
						except OSError as e:
							self.log(str(e))
							self._numdirsfld += 1

					if self._forcecopy:
						os.chmod(dir2, 1911)  # 1911 = 0o777

					sourcefile = os.path.join(dir1, filename)
					try:
						if os.path.islink(sourcefile):
							os.symlink(os.readlink(sourcefile),
									   os.path.join(dir2, filename))
						else:
							shutil.copy2(sourcefile, dir2)
						self._numfiles += 1
					except (IOError, OSError) as e:
						self.log(str(e))
						self._numcopyfld += 1

				if self._copydirection == 1 or self._copydirection == 2:
					# target to source

					if not os.path.exists(dir1):
						if self._forcecopy:
							# 1911 = 0o777
							os.chmod(os.path.dirname(self.dir1_root), 1911)

						try:
							os.makedirs(dir1)
							self._numnewdirs += 1
						except OSError as e:
							self.log(str(e))
							self._numdirsfld += 1

					targetfile = os.path.abspath(os.path.join(dir1, filename))
					if self._forcecopy:
						os.chmod(dir1, 1911)  # 1911 = 0o777

					sourcefile = os.path.join(dir2, filename)

					try:
						if os.path.islink(sourcefile):
							os.symlink(os.readlink(sourcefile),
									   os.path.join(dir1, filename))
						else:
							shutil.copy2(sourcefile, targetfile)
						self._numfiles += 1
					except (IOError, OSError) as e:
						self.log(str(e))
						self._numcopyfld += 1

			except Exception as e:
				self.log('Error copying file %s' % filename)
				self.log(str(e))


	def _dowork(self, dir1, dir2, copyfunc=None, updatefunc=None):
		""" Private attribute for doing work """

		if self._verbose:
			self.log('Source directory: %s:' % dir1)

		self._dcmp = self._compare(dir1, dir2)

		# Files & directories only in target directory
		if self._purge:
			for f2 in self._dcmp.right_only:
				fullf2 = os.path.join(self._dir2, f2)
				if self._verbose:
					logger.info("Удалено: {}".format(fullf2)) #Запись об удалении в файл
					self.log('Deleting %s' % fullf2)
				try:
					if os.path.isfile(fullf2):
						try:
							try:
								os.remove(fullf2)
							except PermissionError as e:
								os.chmod(fullf2, stat.S_IWRITE)
								os.remove(fullf2)
							self._deleted.append(fullf2)
							self._numdelfiles += 1
						except OSError as e:
							self.log(str(e))
							self._numdelffld += 1
					elif os.path.isdir(fullf2):
						try:
							shutil.rmtree(fullf2, True)
							self._deleted.append(fullf2)
							self._numdeldirs += 1
						except shutil.Error as e:
							self.log(str(e))
							self._numdeldfld += 1

				except Exception as e:  # of any use ?
					self.log(str(e))
					continue

		# Files & directories only in source directory
		for f1 in self._dcmp.left_only:
			try:
				st = os.stat(os.path.join(self._dir1, f1))
			except os.error:
				continue

			if stat.S_ISREG(st.st_mode):
				if copyfunc:
					copyfunc(f1, self._dir1, self._dir2)
					self._added.append(os.path.join(self._dir2, f1))
			elif stat.S_ISDIR(st.st_mode):
				to_make = os.path.join(self._dir2, f1)
				if not os.path.exists(to_make):
					os.makedirs(to_make)
					logger.info("Добавлена папка: {}".format(to_make)) #запись о добавлении новой папки в файл
					self._numnewdirs += 1
					self._added.append(to_make)

		# common files/directories
		for f1 in self._dcmp.common:
			try:
				st = os.stat(os.path.join(self._dir1, f1))
			except os.error:
				continue

			if stat.S_ISREG(st.st_mode):
				if updatefunc:
					updatefunc(f1, self._dir1, self._dir2)
			# nothing to do if we have a directory
			
	def _update(self, filename, dir1, dir2):
		""" Private function for updating a file based on
		last time stamp of modification or difference of content"""

		# NOTE: dir1 is source & dir2 is target
		if self._updatefiles:

			file1 = os.path.join(dir1, filename)
			file2 = os.path.join(dir2, filename)

			try:
				st1 = os.stat(file1)
				st2 = os.stat(file2)
			except os.error:
				return -1

			# Update will update in both directions depending
			# on ( the timestamp of the file or its content ) & copy-direction.

			if self._copydirection == 0 or self._copydirection == 2:

				# If flag 'content' is used then look only at difference of file
				# contents instead of time stamps.
				# Update file if file's modification time is older than
				# source file's modification time, or creation time. Sometimes
				# it so happens that a file's creation time is newer than it's
				# modification time! (Seen this on windows)
				need_upd = (not filecmp.cmp(file1, file2, False)) if self._use_content else self._cmptimestamps(st1, st2)
				if need_upd:
					if self._verbose:
						# source to target
						print()
						logger.info("Обновлен файл: {}".format(file2)) #Запись об обновлении файла
						print()
						self.log('Updating file %s' % file2)
					try:
						if self._forcecopy:
							os.chmod(file2, 1638)  # 1638 = 0o666

						try:
							if os.path.islink(file1):
								os.symlink(os.readlink(file1), file2)
							else:
								try:
									shutil.copy2(file1, file2)
								except PermissionError as e:
									os.chmod(file2, stat.S_IWRITE)
									shutil.copy2(file1, file2)
							self._changed.append(file2)
							if self._use_content:
							   self._numcontupdates += 1
							else:
							   self._numtimeupdates += 1
							return 0
						except (IOError, OSError) as e:
							self.log(str(e))
							self._numupdsfld += 1
							return -1

					except Exception as e:
						self.log(str(e))
						return -1

			if self._copydirection == 1 or self._copydirection == 2:

				# No need to do reverse synchronization in case of content comparing.
				# Update file if file's modification time is older than
				# source file's modification time, or creation time. Sometimes
				# it so happens that a file's creation time is newer than it's
				# modification time! (Seen this on windows)
				need_upd = False if self._use_content else self._cmptimestamps(st2, st1)
				if need_upd:
					if self._verbose:
						# target to source
						self.log('Updating file %s' % file1)
					try:
						if self._forcecopy:
							os.chmod(file1, 1638)  # 1638 = 0o666

						try:
							if os.path.islink(file2):
								os.symlink(os.readlink(file2), file1)
							else:
								shutil.copy2(file2, file1)
							self._changed.append(file1)
							self._numtimeupdates += 1
							return 0
						except (IOError, OSError) as e:
							self.log(str(e))
							self._numupdsfld += 1
							return -1

					except Exception as e:
						self.log(str(e))
						return -1

		return -1
	

