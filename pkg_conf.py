import os
import yaml

#########################
# Customizable settings #
#########################

AUTHOR = 'Ivo Flipse'
AUTHOR_EMAIL = 'ivoflipse@gmail.com'
DOC_ROOT = 'docs'
ANACONDA_USER = 'ivoflipse'
PKG_ROOT = 'pawlabeling'
PKG_NAME = 'pawlabeling'
DATA_FILES = ["*.json", "*.zip", "*.png", "*.ini"]

################################
# End of customizable settings #
################################

ABS_REPO_ROOT = os.path.dirname(os.path.realpath(__file__))
_cache = dict()


def get_channels():
    global _cache
    if "channels" not in _cache:
        with open(os.path.join(ABS_REPO_ROOT, 'environment.yml'), "r") as infile:
            environment = yaml.load(infile)
            _cache["channels"] = environment['channels']
    return _cache["channels"]


def get_recipe_meta():
    global _cache
    if 'recipe_meta' not in _cache:
        with open(os.path.join(ABS_REPO_ROOT, 'conda-recipe', 'meta.yaml'), "r") as infile:
            _cache['recipe_meta'] = yaml.load(infile)
    return _cache['recipe_meta']


def get_version():
    global _cache
    if 'version' not in _cache:
        with open(os.path.join(ABS_REPO_ROOT, PKG_ROOT, '__init__.py')) as fid:
            for line in fid:
                if line.startswith('__version__'):
                    _cache['version'] = line.strip().split()[-1][1:-1]
                    break
    return _cache['version']


def get_readme():
    global _cache
    if 'readme' not in _cache:
        with open(os.path.join(ABS_REPO_ROOT, 'readme.md'), "r") as infile:
            _cache['readme'] = infile.read()
    return _cache['readme']


def get_build_number():
    return get_recipe_meta()["build"]["number"]


def get_url():
    return get_recipe_meta()["about"]["home"]
