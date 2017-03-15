all: doc lint test

doc:
	make -C docs html

test:
	coverage run -m doctest gitkv/__init__.py
	# FIXed(Add the following to __init__.py)
	# if __name__ == '__main__':
 	 	#  import doctest
  		#  doctest.testmod()

lint:
	flake8 $$(find . -type f -name '*.py')

fixme:
	find . -type f | xargs grep --color -H -n -i fixme

todo:
	find . -type f | xargs grep --color -H -n -i todo

live:
	find . -type f -name '*.py' | entr make test
