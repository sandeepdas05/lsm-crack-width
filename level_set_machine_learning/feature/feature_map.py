import numpy as np

from level_set_machine_learning.feature.base_feature import (
    BaseFeature, BaseImageFeature, BaseShapeFeature)


class FeatureMap(object):
    """ Stores a set of features and computes their results into a stacked
    multi-dimensional array
    """
    def __init__(self, features):
        """ Initialize a feature map instance

        features: iterable of features
            A list of instances that are subclasses of
            :class:`level_set_machine_learning.feature.BaseFeature`

        """
        self._validate_features(features)
        self.features = set(features)
        self.n_features = len(self.features)

    def _validate_features(self, features):

        if not np.iterable(features):
            raise TypeError("features was not iterable")

        for feature in features:
            if not isinstance(feature, BaseFeature):
                msg = "feature {} was not an instance of {}".format(
                    feature, BaseFeature.__class__.__name__)
                raise ValueError(msg)

        if len(set(features)) != len(features):
            msg = "`features` list included non-unique features"
            raise ValueError(msg)

    def __call__(self, u, img, dist, mask, dx=None):
        """ Compute the features from the feature list.

        Returns
        -------
        features: numpy.array, shape = img.shape + (n_features,)
            The resulting feature array

        """
        features_shape = u.shape + (self.n_features,)
        features_array = np.empty(features_shape)

        for ifeature, feature in enumerate(self.features):
            if isinstance(feature, BaseImageFeature):
                features_array[ifeature][mask] = feature(
                    u=u, img=img, dist=dist, mask=mask, dx=dx)
            elif isinstance(feature, BaseShapeFeature):
                features_array[ifeature][mask] = feature(
                    u=u, dist=dist, mask=mask, dx=dx)
            else:
                msg = "Unknown feature type ({})"
                raise ValueError(msg.format(feature.__class__.__name__))

        return features_array
