from . import PlateAutosave


def getMetaData():
    return {}


def register(app):
    return {"extension": PlateAutosave.PlateAutosave()}
