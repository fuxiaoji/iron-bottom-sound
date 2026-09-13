"""Frozen v13 physical model plus explicit v14 one-factor ablations."""
import math
import numpy as np
from research.experiments.v13_exact import game as v13_game
from research.formation.commitment_v12 import initial_states, enumerate_sequences, trajectory_batch, GRIDS
from research.formation.payoff_v13 import paired_stage
from research.experiments.t1_exact_discrete_certification import fire_vec


def make_game(config, mirror=False):
    g = v13_game(config['geometry'],config['speed'],mirror,config['T'],
                 'rigid_line_ahead' if config.get('ablation')=='rigid' else 'leader_follower')
    g.r0 = config['distance']
    g.xR0 = g.r0*math.cos(math.radians(g.bearing0_deg))
    g.yR0 = g.r0*math.sin(math.radians(g.bearing0_deg))
    return g


def isotropic_fire(k, r):
    # Independent uniform shooter/target headings: angular sector measure
    # (1/6,1/3,1/3,1/6), and target bow/stern measure 1/3.
    out = np.zeros_like(r)
    for d, w in [(0.,1/6),(90.,1/3),(-90.,1/3),(180.,1/6)]:
        for asp, v in [('bow_stern',1/3),('broadside',2/3)]:
            out += w*v*fire_vec(k,r,np.full_like(r,d),np.full(r.shape,asp))
    return out


def isotropic_stage(g, pb, hb, pr, hr):
    out = np.zeros(np.broadcast_shapes(pb.shape[:-2],pr.shape[:-2]))
    for i in range(g.n_ships):
        for j in range(g.n_ships):
            r = np.maximum(np.linalg.norm(pr[...,j,:]-pb[...,i,:],axis=-1),.5)
            out += isotropic_fire(g.kB,r)-isotropic_fire(g.kR,r)
    return out


def matrix(config, mirror=False, chunk=64):
    g = make_game(config, mirror)
    T, levels = config['T'],GRIDS[str(config['grid'])]
    seq = enumerate_sequences(levels,T); b,r = initial_states(g)
    pb,hb = trajectory_batch(b,seq,g);pr,hr = trajectory_batch(r,seq,g)
    A = np.empty((len(seq),len(seq)))
    stage = isotropic_stage if config.get('ablation')=='isotropic' else paired_stage
    for i in range(0,len(seq),chunk):
        L = stage(g,pb[i:i+chunk,None],hb[i:i+chunk,None],pr[None],hr[None])
        if config.get('ablation')=='terminal': A[i:i+chunk] = T*L[...,-1]
        else: A[i:i+chunk] = (L[...,:-1]+L[...,1:]).sum(-1)/2
    return A
