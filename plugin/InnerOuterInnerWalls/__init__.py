# Adds the inner/outer/inner choice to the "Wall Ordering" (inset_direction) setting.
# The slicing itself is done by the patched CuraEngine, see ~/cura-engine-ioi.
from . import InnerOuterInnerWalls


def getMetaData():
    return {}


def register(app):
    return {"extension": InnerOuterInnerWalls.InnerOuterInnerWalls()}
