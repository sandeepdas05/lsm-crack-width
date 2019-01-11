import os

import h5py
import numpy
import skfmm


TRAINING_DATASET_KEY = 'training-dataset'
VALIDATION_DATASET_KEY = 'validation-dataset'
TESTING_DATASET_KEY = 'testing-dataset'
DATASET_KEYS = (
    TRAINING_DATASET_KEY,
    VALIDATION_DATASET_KEY,
    TESTING_DATASET_KEY
)
EXAMPLE_KEY = "example-{:d}"
IMAGE_KEY = "image"
SEGMENTATION_KEY = "segmentation"
DISTANCE_TRANSFORM_KEY = "distance-transform"


class DatasetsManager(object):
    """ Handles internal dataset operations
    """

    def __init__(self, logger, h5_file, imgs=None, segs=None,
                 dx=None, compress=True):
        """ Initialize a dataset manager

        Parameters
        ----------
        logger: logging.Logger
            A logger for logging progress and errors

        h5_file: str
            A (possibly already existing) hdf5 dataset

        imgs: List(ndarray), default=None
            List of images. Necessary when `h5_file` doe not exist.

        segs: List(ndarray), default=None
            List of respective segmentations for :code:`imgs`. Necessary when
            `h5_file` doe not exist.

        dx: List(ndarray), default=None
            The delta spacing along the axis directions in the provided
            images and segmentations. Used when `h5_file` doesn't exist. In
            that case, the default of None uses all ones.

        compress: bool, default=True
            When the image and segmentation data are stored in the hdf5 file
            this flag indicates whether or not to use compression.

        Note
        ----
        Either :code:`h5_file` should be the name of an existing h5 file with
        appropriate structure (see :method:`convert_to_hdf5`) or `imgs`
        and `segs` should be non-None, and the hdf5 file will creating
        using the provided images and segmentations and we be named with the
        argument `h5_file`.

        """
        self.logger = logger

        self.h5_file = os.path.abspath(h5_file)

        if not os.path.exists(self.h5_file):
            if imgs is None or segs is None:
                msg = ("Provided `h5_file` {} doesn't exist but no image or "
                       "segmentation data provided")
                raise ValueError(msg.format(h5_file))

            # Perform the conversion to hdf5
            self.convert_to_hdf5(imgs=imgs, segs=segs,
                                 dx=dx, compress=compress)

        # To be assigned by a `split` method
        self.datasets = {}

        with h5py.File(self.h5_file) as hf:
            self.n_examples = len(hf.keys())

    def convert_to_hdf5(self, imgs, segs, dx=None, compress=True):
        """ Convert a dataset of images and boolean segmentations
        to hdf5 format, which is required for the level set routine.

        The format assuming `hf` is and h5py `File` is as follows::

            'i'
            |_ img
            |_ seg
            |_ dist
            |_ attrs
               |_ dx

        Parameters
        ----------
        imgs: List(ndarray)
            The list of image examples for the dataset.

        segs: List(ndarray)
            The list of image examples for the dataset.

        dx: ndarray, shape=(nexamples, img.ndim), default=None
            The resolutions along each axis for each image. The default (None)
            assumes the resolution is 1 along each axis direction, but this
            might not be the case for anisotropic data.

        compress: bool, default=True
            If True, :code:`gzip` compression with default compression
            options (level=4) is used for the images and segmentations.

        """
        # Check if the file already exists and abort if so.
        if os.path.exists(self.h5_file):
            msg = "Dataset already exists at {}"
            raise FileExistsError(msg.format(self.h5_file))

        # Setup some variables
        n_examples = len(imgs)
        ndim = imgs[0].ndim
        compress_method = "gzip" if compress else None

        ######################
        # Input validation

        if len(imgs) != len(segs):
            msg = "Mismatch in number of examples: imgs ({}), segs ({})"
            raise ValueError(msg.format(len(imgs), len(segs)))

        for i in range(n_examples):
            img = imgs[i]
            seg = segs[i]

            # Validate image data type
            if img.dtype != numpy.float:
                msg = "imgs[{}] (dtype {}) was not float"
                raise TypeError(msg.format(i, img.dtype))

            # Validate segmentation data type
            if seg.dtype != numpy.bool:
                msg = "seg[{}] (dtype {}) was not bool"
                raise TypeError(msg.format(i, seg.dtype))

            if img.ndim != ndim:
                msg = "imgs[{}] (ndim={}) did not have correct dimensions ({})"
                raise ValueError(msg.format(i, img.ndim, ndim))

            if seg.ndim != ndim:
                msg = "segs[{}] (ndim={}) did not have correct dimensions ({})"
                raise ValueError(msg.format(i, seg.ndim, ndim))

            if img.shape != img.shape:
                msg = "imgs[{}] shape {} does not match segs[{}] shape {}"
                raise ValueError(msg.format(i, img.shape, i, seg.shape))

        # Check dx if provided and is correct shape.
        if dx is None:
            dx = numpy.ones((n_examples, ndim), dtype=numpy.float)
        else:
            if dx.shape != (n_examples, ndim):
                msg = "`dx` was shape {} but should be shape {}"
                raise ValueError(msg.format(dx.shape, (n_examples, ndim)))

        # End input validation
        ##########################

        hf = h5py.File(self.h5_file, 'w')

        for i in range(n_examples):

            msg = "Creating dataset entry {} / {}"
            self.logger.info(msg.format(i+1, n_examples))

            # Create a group for the i'th example
            g = hf.create_group(EXAMPLE_KEY.format(i))

            # Store the i'th image and segmentation
            g.create_dataset(IMAGE_KEY,
                             data=imgs[i], compression=compress_method)
            g.create_dataset(SEGMENTATION_KEY,
                             data=segs[i], compression=compress_method)

            # Compute the signed distance transform of the ground-truth
            # segmentation and store it.
            dist = skfmm.distance(2*segs[i].astype(numpy.float)-1, dx=dx[i])
            g.create_dataset(DISTANCE_TRANSFORM_KEY,
                             data=dist, compression=compress_method)

            # Store the delta terms as an attribute.
            g.attrs['dx'] = dx[i]

        # Close up shop
        hf.close()

    def split_datasets(self,
                       training_dataset_indices,
                       validation_dataset_indices,
                       testing_dataset_indices):
        """ Specify which of the data should belong to training, validation,
        and testing datasets. Automatic randomization is possible: see keyword
        argument parameters.

        Parameters
        ----------
        training_dataset_indices: List(int)
            The list of indices of examples that belong to the training dataset

        validation_dataset_indices: List(int)
            The list of indices of examples that belong to the validation
            dataset

        testing_dataset_indices: List(int)
            The list of indices of examples that belong to the testing dataset

        """

        if not all([isinstance(index) for index in training_dataset_indices]):
            msg = "Training data indices must be a list of integers"
            raise ValueError(msg)

        if not all([isinstance(index)
                    for index in validation_dataset_indices]):
            msg = "Validation data indices must be a list of integers"
            raise ValueError(msg)

        if not all([isinstance(index) for index in testing_dataset_indices]):
            msg = "Training data indices must be a list of integers"
            raise ValueError(msg)

        self.datasets[TRAINING_DATASET_KEY] = training_dataset_indices
        self.datasets[VALIDATION_DATASET_KEY] = validation_dataset_indices
        self.datasets[TESTING_DATASET_KEY] = testing_dataset_indices

    def split_datasets_random(self, keys, random_state,
                              probabilities=(0.6, 0.2, 0.2), subset_size=None):
        """
        Split a list `keys` randomly into training, validation,
        and testing sets

        Parameters
        ----------
        keys: list of strings
            List of keys to split into training, validation, and testing

        random_state: numpy.random.RandomState
            For reproducible results

        probabilities: 3-tuple of floats, default=(0.6, 0.2, 0.2)
            The probability of being placed in the training, validation
            or testing

        subset_size: int, default=None
            If provided, then should be less than or equal to
            :code:`len(keys)`. If given, then :code:`keys` is first
            sub-sampled by :code:`subset_size`
            before splitting.

        """
        if subset_size is not None and subset_size > len(keys):
            raise ValueError("`subset_size` must be <= `len(keys)`.")

        if subset_size is None:
            subset_size = len(keys)

        sub_keys = random_state.choice(keys, replace=False, size=subset_size)
        n_keys = len(sub_keys)

        # This generates a matrix size `(n_keys, 3)` where each row
        # is an indicator vector indicating to which dataset the key with
        # respective row index should be placed into.
        indicators = random_state.multinomial(1, pvals=probabilities,
                                              size=n_keys)

        # Cast to numpy array for fancy indexing
        sub_keys_as_array = numpy.array(sub_keys)

        for idataset_key, dataset_key in enumerate(_iterate_dataset_keys()):

            indices_for_dataset_key = numpy.where(indicators == idataset_key)
            as_list = list(sub_keys_as_array[indices_for_dataset_key])
            self.datasets[dataset_key] = as_list


def _iterate_dataset_keys():

    for dataset_key in DATASET_KEYS:
        yield dataset_key
