# packaging
build:
	python -m build

publish-test:
	twine upload -r testpypi dist/*

publish:
	twine upload dist/*
