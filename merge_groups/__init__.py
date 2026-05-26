from krita import Krita

from .extension import MergeGroupsExtension

Krita.instance().addExtension(MergeGroupsExtension(Krita.instance()))
