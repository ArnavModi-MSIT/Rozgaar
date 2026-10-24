"""Explicit package imports; reader storage stays independent of career storage."""
import importlib
from rozgaar.paths import ROOT as APP_ROOT, READER_CODE as READER_ROOT

def reader_modules():
    return (importlib.import_module("url_reader.dashboard"),
            importlib.import_module("url_reader.identity"),
            importlib.import_module("url_reader.quality"))
