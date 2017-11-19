import os

import torch
from torch.utils.data import Dataset

from ..graph.geometry import edges_from_faces
from .utils.dir import make_dirs
from .utils.ply import read_ply
from .data import Data


class FAUST(Dataset):
    """`MPI FAUST <http://faust.is.tue.mpg.de>`_ Dataset.

    Args:
        root (string): Root directory of dataset where ``raw/MPI-FAUST`` exist.
        train (bool, optional): If True, creates dataset from ``training.pt``,
            otherwise from ``test.pt``. (default: ``True``)
        distance (bool, optional): Whether to load additional geodesic distance
            information for each example. (default: ``False``)
        transform (callable, optional): A function/transform that takes in an
            ``Data`` object and returns a transformed version.
            (default: ``None``)
    """

    url = 'http://faust.is.tue.mpg.de/'
    diam_url = 'http://www.roemisch-drei.de/faust_shot.tar.gz'

    n_training = 80
    n_test = 20

    def __init__(self, root, train=True, distance=False, transform=None):
        super(FAUST, self).__init__()

        self.root = os.path.expanduser(root)
        self.raw_folder = os.path.join(self.root, 'raw', 'MPI-FAUST')
        self.processed_folder = os.path.join(self.root, 'processed')

        self.training_file = os.path.join(self.processed_folder, 'training.pt')
        self.test_file = os.path.join(self.processed_folder, 'test.pt')

        self.train = train
        self.distance = distance
        self.transform = transform

        self.download()
        self.process()

        data_file = self.training_file if train else self.test_file
        self.index, self.position = torch.load(data_file)

    def __getitem__(self, i):
        index = self.index[i]
        weight = torch.FloatTensor(index.size(1)).fill_(1)
        adj = torch.sparse.FloatTensor(index, weight, torch.Size([6890, 6890]))
        position = self.position[i]
        data = Data(None, adj, position, None)

        if self.transform is not None:
            data = self.transform(data)

        return data.all()

    def __len__(self):
        return self.n_training if self.train else self.n_test

    def _raw_exists(self):
        return os.path.exists(self.raw_folder)

    def _processed_exists(self):
        return os.path.exists(self.processed_folder)

    def _read_example(self, index):
        path = os.path.join(self.raw_folder, 'training', 'registrations',
                            'tr_reg_{0:03d}.ply'.format(index))

        position, face = read_ply(path)
        index = edges_from_faces(face)

        return index, position

    def _save_examples(self, indices, path):
        data = [self._read_example(i) for i in indices]

        index = torch.stack([example[0] for example in data], dim=0)
        position = torch.stack([example[1] for example in data], dim=0)

        torch.save((index, position), path)

    def download(self):
        if not self._raw_exists():
            raise RuntimeError('Dataset not found. Please download it from ' +
                               '{}'.format(self.url))

    def process(self):
        if self._processed_exists():
            return

        print('Processing...')

        make_dirs(os.path.join(self.processed_folder))

        train_indices = range(0, self.n_training)
        self._save_examples(train_indices, self.training_file)

        test_indices = range(self.n_training, self.n_training + self.n_test)
        self._save_examples(test_indices, self.test_file)

        print('Done!')
