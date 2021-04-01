pip-compile:
	pip-compile -r requirements.in && pip-compile -r dev-requirements.in && pip-sync dev-requirements.txt

webpack:
	npx webpack --config webpack.config.js

hooks:
	pre-commit run --files $$(git ls-files -m)
