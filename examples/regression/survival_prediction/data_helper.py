import glob
import json
import os
import os.path as osp
import pickle

import numpy as np
from extract_patch_feature import extract_ft
from torch.utils.data import Dataset
from torch.utils.data.dataset import T_co

from HyperG.utils.data import split_id
from HyperG.utils.data.pathology import sample_patch_coors, draw_patches_on_slide


def split_train_val(data_root, ratio=0.8, save_split_dir=None, resplit=False):
    if not resplit and save_split_dir is not None and osp.exists(save_split_dir):
        with open(save_split_dir, 'rb') as f:
            result = pickle.load(f)
        return result

    all_list = glob.glob(osp.join(data_root, '*.svs'))
    with open(osp.join(data_root, 'opti_survival.json'), 'r') as fp:
        lbls = json.load(fp)

    all_dict = {}
    for full_dir in all_list:
        id = get_id(full_dir)
        all_dict[id]['img_dir'] = full_dir
        all_dict[id]['survival_time'] = lbls[id]

    id_list = list(all_dict.keys())
    train_list, val_list = split_id(id_list, ratio)

    train_list = [all_dict[_id] for _id in train_list]
    val_list = [all_dict[_id] for _id in val_list]

    result = {'train': train_list, 'val': val_list}
    if save_split_dir is not None:
        save_folder = osp.split(save_split_dir)[0]
        if not osp.exists(save_folder):
            os.makedirs(save_folder)
        with open(save_split_dir, 'wb') as f:
            pickle.dump(result, f)

    return result


def preprocess(data_dict, patch_ft_dir, patch_coors_dir, num_sample=2000,
               patch_size=256, sampled_vis=None, mini_frac=32):
    # check if each slide patch feature exists
    all_dir_list = []
    for phase in ['train', 'val']:
        for _dir in data_dict[phase]:
            all_dir_list.append(_dir['img_dir'])
    to_do_list = check_patch_ft(all_dir_list, patch_ft_dir)

    if to_do_list is not None:
        for _idx, _dir in enumerate(to_do_list):
            print(f'processing {_idx + 1}/{len(to_do_list)}...')
            _id = get_id(_dir)
            _patch_coors = sample_patch_coors(_dir, num_sample=2000, patch_size=256)

            # save sampled patch coordinates
            with open(osp.join(patch_coors_dir, f'{_id}_coors.pkl')) as fp:
                pickle.dump(_patch_coors, fp)

            # visualize sampled patches on slide
            if sampled_vis is not None:
                _vis_img = draw_patches_on_slide(_dir, _patch_coors, mini_frac=32)
                with open(osp.join(sampled_vis, f'{_id}_sampled_patches.jpg')) as fp:
                    _vis_img.save(fp)

    # extract patch feature for each slide
    for _dir in all_dir_list:
        _id = get_id(_dir)
        _patch_coors = None
        fts = extract_ft(_dir, _patch_coors)
        np.save(osp.join(patch_ft_dir, f'{_id}_fts.npy'), fts.cpu().numpy())


def get_dataloader(data_dict, patch_ft_dir):
    pass


class slide_patch(Dataset):

    def __getitem__(self, index: int) -> T_co:
        return super().__getitem__(index)

    def __len__(self) -> int:
        return super().__len__()


def check_patch_ft(dir_list, patch_ft_dir):
    to_do_list = []
    done_list = glob.glob(osp.join(patch_ft_dir, '*_ft.npy'))
    done_list = [get_id(_dir).split('_ft.')[0] for _dir in done_list]
    for _dir in dir_list:
        id = get_id(_dir)
        if id not in done_list:
            to_do_list.append(_dir)
    return to_do_list


def get_id(_dir):
    return osp.splitext(osp.split(_dir)[1])[0]
