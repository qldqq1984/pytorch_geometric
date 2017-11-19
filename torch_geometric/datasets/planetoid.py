from __future__ import print_function

import os

import torch
from torch.utils.data import Dataset

from .data import Data
from .utils.dir import make_dirs
from .utils.download import download_url
from .utils.planetoid import read_planetoid


class Planetoid(Dataset):
    url = "https://github.com/kimiyoung/planetoid/raw/master/data"

    def __init__(self, root, name, transform=None):
        super(Planetoid, self).__init__()

        # Set dataset properites.
        self.root = os.path.expanduser(root)
        self._name = name
        self.raw_folder = os.path.join(self.root, 'raw')
        self.processed_folder = os.path.join(self.root, 'processed')
        self.data_file = os.path.join(self.processed_folder, 'data.pt')
        self.transform = transform

        # Download and process.
        self.download()
        self.process()

        # Load processed data.
        data = torch.load(self.data_file)
        input, index, target = data

        # Create unweighted sparse adjacency matrix.
        weight = torch.ones(index.size(1))
        n = input.size(0)
        adj = torch.sparse.FloatTensor(index, weight, torch.Size([n, n]))

        # Bundle graph to data object.
        self.data = Data(input, adj, position=None, target=target)

    def __getitem__(self, index):
        data = self.data

        if self.transform is not None:
            data = self.transform(data)

        return data.all()

    def __len__(self):
        return 1

    @property
    def _raw_exists(self):
        return os.path.exists(self.raw_folder)

    @property
    def _processed_exists(self):
        return os.path.exists(self.processed_folder)

    def download(self):
        if self._raw_exists:
            return

        print('Downloading {}'.format(self.url))

        ext = ['tx', 'ty', 'allx', 'ally', 'graph']
        for e in ext:
            url = '{}/ind.{}.{}'.format(self.url, self._name, e)
            download_url(url, self.raw_folder)

    def process(self):
        if self._processed_exists:
            return

        print('Processing...')

        make_dirs(os.path.join(self.processed_folder))
        data = read_planetoid(self.raw_folder, self._name)
        torch.save(data, self.data_file)

        print('Done!')
