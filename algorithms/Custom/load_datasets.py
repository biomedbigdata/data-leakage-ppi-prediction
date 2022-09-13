import numpy as np
import random
from tqdm import tqdm
from sklearn.model_selection import train_test_split


def read_nodelist(path):
    id_dict = dict()
    with open(path, 'r') as f:
        for line in f:
            line_split = line.strip().split("\t")
            id_dict[line_split[1]] = int(line_split[0])
    return id_dict


def read_matrix_colnames(path):
    id_dict = dict()
    idx = 0
    with open(path, 'r') as f:
        for line in f:
            id_dict[line.strip()] = idx
            idx += 1
    return id_dict


def node2vec_embeddings_to_dict(embed_pth):
    """
    read the embeddings generated by Node2vec
    :return dict of id -> embeddings
    """
    # load the embeddings generated by node2vec for each index GO, ignore first information line
    embeddings_dict = {}
    embeddings = open(embed_pth).read().splitlines()[1:]
    embeddings = [x.split(" ") for x in embeddings]

    for i in range(0, len(embeddings)):
        # set the id as the key
        key = int(embeddings[i][0])
        # add all the dimension of the embedings as a list of floats
        embeddings_dict[key] = [float(x) for x in embeddings[i][1:]]

    return embeddings_dict


def load_encoding(encoding='PCA', organism='yeast'):
    dim_reds = {'PCA', 'MDS', 'node2vec'}
    if encoding not in dim_reds:
        raise ValueError("encoding must be one of %r." % dim_reds)
    if encoding == 'PCA':
        if organism == 'yeast':
            emb = np.load('data/yeast_pca.npy')
            id_dict = read_matrix_colnames('../../network_data/SIMAP2/matrices/sim_matrix_yeast_colnames.txt')
        else:
            emb = np.load('data/human_pca.npy')
            id_dict = read_matrix_colnames('../../network_data/SIMAP2/matrices/sim_matrix_human_colnames.txt')

    elif encoding == 'MDS':
        if organism == 'yeast':
            emb = np.load('data/yeast_mds.npy')
            id_dict = read_matrix_colnames('../../network_data/SIMAP2/matrices/sim_matrix_yeast_colnames.txt')
        else:
            emb = np.load('data/human_mds.npy')
            id_dict = read_matrix_colnames('../../network_data/SIMAP2/matrices/sim_matrix_human_colnames.txt')

    else:
        if organism == 'yeast':
            emb = node2vec_embeddings_to_dict('data/yeast.emb')
            id_dict = read_nodelist('data/yeast.nodelist')
        else:
            emb = node2vec_embeddings_to_dict('data/human.emb')
            id_dict = read_nodelist('data/human.nodelist')
    return emb, id_dict


def make_X_y(ppis, emb, id_dict):
    X = np.empty(shape=(len(ppis), 256))
    y = np.empty(shape=(len(ppis)), dtype=int)
    for i, ppi in enumerate(ppis):
        idx_0 = id_dict[ppi[0]]
        idx_1 = id_dict[ppi[1]]
        label = ppi[2]
        emb0 = emb[idx_0]
        emb1 = emb[idx_1]
        X[i] = np.append(emb0, emb1)
        y[i] = label
    return X, y


def read_from_SPRINT(encoding, emd, id_dict, path, label):
    ppis = []
    with open(path, 'r') as f:
        for line in f:
            line_split = line.strip().split(' ')
            uid0 = line_split[0]
            uid1 = line_split[1]
            if id_dict.get(uid0) is not None and id_dict.get(uid1) is not None:
                if encoding == 'node2vec':
                    id0 = id_dict[uid0]
                    id1 = id_dict[uid1]
                    if id0 in emd.keys() and id1 in emd.keys():
                        ppis.append([uid0, uid1, label])
                else:
                    ppis.append([uid0, uid1, label])
    return ppis


def load_from_SPRINT(encoding='PCA', dataset='huang', rewire=False):
    if dataset in ['guo', 'du']:
        organism = 'yeast'
    else:
        organism = 'human'
    emd, id_dict = load_encoding(encoding=encoding, organism=organism)
    if rewire:
        folder = 'rewired'
    else:
        folder = 'original'
    train_pos = read_from_SPRINT(encoding, emd, id_dict, f'../SPRINT/data/{folder}/{dataset}_train_pos.txt', '1')
    train_neg = read_from_SPRINT(encoding, emd, id_dict, f'../SPRINT/data/{folder}/{dataset}_train_neg.txt', '0')
    train_pos.extend(train_neg)
    train_pos = balance_set(train_pos, id_dict, encoding, emd)

    test_pos = read_from_SPRINT(encoding, emd, id_dict, f'../SPRINT/data/{folder}/{dataset}_test_pos.txt', '1')
    test_neg = read_from_SPRINT(encoding, emd, id_dict, f'../SPRINT/data/{folder}/{dataset}_test_neg.txt', '0')
    test_pos.extend(test_neg)
    test_pos = balance_set(test_pos, id_dict, encoding, emd)

    X_train, y_train = make_X_y(train_pos, emd, id_dict)
    X_test, y_test = make_X_y(test_pos, emd, id_dict)
    return X_train, y_train, X_test, y_test


def balance_set(ppis, id_dict, encoding, emd):
    pos_len = sum([int(pair[2]) for pair in ppis])
    neg_len = len(ppis) - pos_len
    if pos_len > neg_len:
        print(f'sampling more negatives ({pos_len} positives, {neg_len} negatives)...')
        if encoding == 'node2vec':
            candidates = [key for key, value in id_dict.items() if value in emd.keys()]
        else:
            candidates = [key for key, value in id_dict.items()]

        while pos_len > neg_len:
            prot1 = random.choice(tuple(candidates))
            prot1_list = [pair[0] for pair in ppis if pair[1] == prot1] + [pair[1] for pair in ppis if
                                                                                pair[0] == prot1]
            # protein should occur in the dataset
            while len(prot1_list) == 0:
                prot1 = random.choice(tuple(candidates))
                prot1_list = [pair[0] for pair in ppis if pair[1] == prot1] + [pair[1] for pair in ppis if
                                                                                    pair[0] == prot1]
            prot2 = random.choice(tuple(candidates))
            prot2_list = [pair[0] for pair in ppis if pair[1] == prot2] + [pair[1] for pair in ppis if
                                                                                pair[0] == prot2]
            node2vec_valid=True
            if encoding == 'node2vec' and (id_dict[prot1] not in emd.keys() or id_dict[prot2] not in emd.keys()):
                node2vec_valid=False

            while prot1 == prot2 or prot2 in prot1_list or len(prot2_list) == 0 or not node2vec_valid:
                prot2 = random.choice(tuple(candidates))
                prot2_list = [pair[0] for pair in ppis if pair[1] == prot2] + [pair[1] for pair in ppis if
                                                                                    pair[0] == prot2]
                if encoding == 'node2vec' and (id_dict[prot1] not in emd.keys() or id_dict[prot2] not in emd.keys()):
                    node2vec_valid = False
                elif encoding == 'node2vec' and id_dict[prot1] in emd.keys() and id_dict[prot2] in emd.keys():
                    node2vec_valid = True
            ppis.append([prot1, prot2, '0'])
            neg_len += 1
    else:
        print(f'randomly dropping negatives ({pos_len} positives, {neg_len} negatives)...')
        pos_ppis = [x for x in ppis if x[2] == '1']
        neg_ppis = [x for x in ppis if x[2] == '0']
        to_delete = set(random.sample(range(len(neg_ppis)), len(neg_ppis) - len(pos_ppis)))
        neg_ppis = [x for i, x in enumerate(neg_ppis) if not i in to_delete]
        ppis = pos_ppis
        ppis.extend(neg_ppis)
    return ppis


def make_swissprot_to_dict(path_to_swissprot):
    prefix_dict = {}
    seq_dict = {}
    header_line = False
    last_id = ''
    last_seq = ''
    n = 30
    f = open(path_to_swissprot, 'r')
    for line in f:
        if line.startswith('>'):
            if last_id != '':
                seq_dict[last_id] = last_seq
                last_seq = ''
            header_line = True
            uniprot_id = line.split('|')[1]
            last_id = uniprot_id
        elif header_line is True:
            last_seq += line.strip()
            first_n = line[0:n]
            if first_n in prefix_dict.keys():
                if isinstance(prefix_dict[first_n], list):
                    prefix_dict[first_n].append(last_id)
                else:
                    prefix_dict[first_n] = [prefix_dict[first_n], last_id]
            else:
                prefix_dict[first_n] = last_id
            header_line = False
        else:
            last_seq += line.strip()
    f.close()
    return prefix_dict, seq_dict


def read_in_partitions(lines, id_dict, emd, encoding, label):
    from tqdm import tqdm
    ppis = []
    for line in tqdm(lines):
        line_split = line.strip().split(' ')
        id0_uniprot = line_split[0]
        id1_uniprot = line_split[1]
        if id0_uniprot in id_dict.keys() and id1_uniprot in id_dict.keys():
            id0 = id_dict[line_split[0]]
            id1 = id_dict[line_split[1]]
            if encoding == 'node2vec' and id0 in emd.keys() and id1 in emd.keys():
                ppis.append([id0_uniprot, id1_uniprot, label])
            elif encoding != 'node2vec':
                ppis.append([id0_uniprot, id1_uniprot, label])
    return ppis


def load_partition_datasets(encoding, dataset, partition_train, partiton_test):
    dataset_choices = {'du', 'guo', 'huang', 'pan', 'richoux'}
    if dataset not in dataset_choices:
        raise ValueError('dataset must be one of %r.' % dataset_choices)
    partition_choices = {'0', '1', 'both'}
    if partition_train not in partition_choices or partiton_test not in partition_choices:
        raise ValueError('partition must be one of %r', partition_choices)
    if dataset in {'guo', 'du'}:
        organism='yeast'
    else:
        organism='human'
    print(f'Loading {encoding} encoding ...')
    emd, id_dict = load_encoding(encoding=encoding, organism=organism)
    train_pos = open(f'../SPRINT/data/partitions/{dataset}_partition_{partition_train}_pos.txt').readlines()
    X_train = read_in_partitions(lines=train_pos,
                               id_dict=id_dict, emd=emd, encoding=encoding,
                               label='1')
    train_neg = open(f'../SPRINT/data/partitions/{dataset}_partition_{partition_train}_neg.txt').readlines()
    X_train.extend(read_in_partitions(lines=train_neg,
                               id_dict=id_dict, emd=emd, encoding=encoding,
                               label='0'))
    test_pos = open(f'../SPRINT/data/partitions/{dataset}_partition_{partiton_test}_pos.txt').readlines()
    X_test = read_in_partitions(lines=test_pos,
                               id_dict=id_dict, emd=emd, encoding=encoding,
                               label='1')
    test_neg = open(f'../SPRINT/data/partitions/{dataset}_partition_{partiton_test}_neg.txt').readlines()
    X_test.extend(read_in_partitions(lines=test_neg,
                               id_dict=id_dict, emd=emd, encoding=encoding,
                               label='0'))
    X_train = balance_set(X_train, id_dict, encoding, emd)
    X_train, y_train = make_X_y(np.array(X_train), emd, id_dict)
    X_test = balance_set(X_test, id_dict, encoding, emd)
    X_test, y_test = make_X_y(np.array(X_test), emd, id_dict)
    return X_train, y_train, X_test, y_test