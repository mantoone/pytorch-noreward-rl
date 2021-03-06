"""""""""
Pytorch implementation of Curiosity-driven Exploration by Self-supervised Prediction (https://pathak22.github.io/noreward-rl/resources/icml17.pdf).
Source code is heavily based on ikostrikov's A3C (https://github.com/ikostrikov/pytorch-a3c/blob/master/LICENSE.md)
"""""""""
from __future__ import print_function

import time
import argparse
import os
import sys

import torch
import torch.optim as optim
import torch.multiprocessing as mp
import torch.nn as nn
import torch.nn.functional as F
#from envs import create_atari_env
import env_wrapper
from model import ActorCritic
from train import train
from test import test
import my_optim
import gym

# Based on
# https://github.com/pytorch/examples/tree/master/mnist_hogwild
# Training settings
parser = argparse.ArgumentParser(description='A3C')
parser.add_argument('--lr', type=float, default=0.001, metavar='LR',
                    help='learning rate (default: 0.0001)')
parser.add_argument('--gamma', type=float, default=0.99, metavar='G',
                    help='discount factor for rewards (default: 0.99)')
parser.add_argument('--tau', type=float, default=1.00, metavar='T',
                    help='parameter for GAE (default: 1.00)')
parser.add_argument('--seed', type=int, default=1, metavar='S',
                    help='random seed (default: 1)')
parser.add_argument('--num-processes', type=int, default=4, metavar='N',
                    help='how many training processes to use (default: 4)')
parser.add_argument('--num-steps', type=int, default=20, metavar='NS',
                    help='number of forward steps in A3C (default: 20)')
parser.add_argument('--max-episode-length', type=int, default=10000, metavar='M',
                    help='maximum length of an episode (default: 10000)')
parser.add_argument('--env-name', default='PongDeterministic-v0', metavar='ENV',
                    help='environment to train on (default: PongDeterministic-v0)')
parser.add_argument('--no-shared', default=False, metavar='O',
                    help='use an optimizer without shared momentum.')
####################
parser.add_argument('--eta', type=float, default=0.01, metavar='LR',
                    help='scaling factor for intrinsic reward')
parser.add_argument('--beta', type=float, default=0.2, metavar='LR',
                    help='balance between inverse & forward')
parser.add_argument('--lmbda', type=float, default=0.1, metavar='LR',
                    help='lambda : balance between A3C & icm')

parser.add_argument('--outdir', default="../output", help='Output log directory')
parser.add_argument('--record', action='store_true', help="Record the policy running video")



if __name__ == '__main__':
    args = parser.parse_args()
    torch.manual_seed(args.seed)

    #mp.set_start_method('spawn')

    env = env_wrapper.create_atari_env(args.env_name)
    #env = gym.make('MontezumaRevenge-v0')
    #env = env_wrapper.create_doom(args.record, outdir=args.outdir)
    shared_model = ActorCritic(
        env.observation_space.shape[0], env.action_space)
    shared_model.share_memory()

    if args.no_shared:
        optimizer = None
    else:
        optimizer = my_optim.SharedAdam(shared_model.parameters(), lr=args.lr)
        optimizer.share_memory()

    processes = []

    rank = 0
    #print('Train without multiprocessing')
    #test(rank, args, shared_model)
    train(rank, args, shared_model, optimizer, True)
    #print('Training done')

    p = mp.Process(target=test, args=(args.num_processes, args, shared_model))
    p.start()
    processes.append(p)
    time.sleep(0.1)

    for rank in range(0, args.num_processes):
        p = mp.Process(target=train, args=(rank, args, shared_model, optimizer, rank == 0))
        p.start()
        time.sleep(0.1)
        processes.append(p)
    for p in processes:
        p.join()
