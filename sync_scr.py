import sys
import time
import threading
from dirsync import sync
from newsyncer.newsyncer import NewSyncer

# source_path = r'C:\\users\gosu\desktop\from'
# target_path = r'C:\\users\gosu\desktop\to'
source_path = '{}'.format(sys.argv[1])
target_path = '{}'.format(sys.argv[2])
print(source_path)
print(target_path)
def thread_():
	print(time.ctime())
	def sync(sourcedir, targetdir, action, **options):
		copier = NewSyncer(source_path, target_path, 'sync', verbose=True, purge=True)
		copier.do_work()
		# print report at the end
		copier.report()
		return set(copier._changed).union(copier._added).union(copier._deleted)
	sync(source_path, target_path, 'sync', verbose=True, purge=True)
	threading.Timer(int(sys.argv[3]), thread_).start()
	

if __name__ == '__main__':
	thread_()
