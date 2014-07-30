# coding: utf-8

""" Test action-angle stuff """

from __future__ import division, print_function

__author__ = "adrn <adrn@astro.columbia.edu>"

# Standard library
import os, sys
import logging

# Third-party
import matplotlib.pyplot as plt
import numpy as np
from astropy import log as logger
import astropy.units as u

# Project
from ...integrate import LeapfrogIntegrator
from ...potential.lm10 import LM10Potential
from ..actionangle import *

logger.setLevel(logging.DEBUG)

plot_path = "plots/tests/dynamics/actionangle"
if not os.path.exists(plot_path):
    os.makedirs(plot_path)

# HACK:
sys.path.append("/Users/adrian/Downloads/genfunc-master")
import genfunc_3d

def angmom(x):
    return np.array([x[1]*x[5]-x[2]*x[4],x[2]*x[3]-x[0]*x[5],x[0]*x[4]-x[1]*x[3]])

def sanders_classify(X):
    L=angmom(X[0])
    loop = np.array([1,1,1])
    for i in X[1:]:
        L0 = angmom(i)
        if(L0[0]*L[0]<0.):
            loop[0] = 0
        if(L0[1]*L[1]<0.):
            loop[1] = 0
        if(L0[2]*L[2]<0.):
            loop[2] = 0
    return loop

def test_classify():
    usys = (u.kpc, u.Msun, u.Myr)
    potential = NFWPotential(v_h=(121.858*u.km/u.s).decompose(usys).value,
                             r_h=20., q1=0.86, q2=1., q3=1.18, usys=usys)
    acc = lambda t,x: potential.acceleration(x)
    integrator = LeapfrogIntegrator(acc)

    # initial conditions
    loop_w0 = [[6.975016793191392, -93.85342183505938, -71.90978460109265, -0.19151220547102255, -0.5944685489722188, 0.4262481187389783], [-119.85377948180077, -50.68671610744867, -10.05148560039928, -0.3351091185863992, -0.42681239582943836, -0.2512200315205476]]
    t,loop_ws = integrator.run(loop_w0, dt=1., nsteps=15000)

    box_w0 = [[57.66865614916953, -66.09241133078703, 47.43779192106421, -0.6862780950091272, 0.04550073987392385, -0.36216991360120393], [-12.10727872905934, -17.556470673741607, 7.7552881580976, -0.1300187288715955, -0.023618199542192752, 0.08686283408067244]]
    t,box_ws = integrator.run(box_w0, dt=1., nsteps=15000)

    # my classify
    orb_type = classify_orbit(loop_ws)
    for j in range(len(loop_w0)):
        assert np.all(orb_type[j] == sanders_classify(loop_ws[:,j]))

    orb_type = classify_orbit(box_ws)
    for j in range(len(box_w0)):
        assert np.all(orb_type[j] == sanders_classify(box_ws[:,j]))

def plot_orbit(w,ix=None):
    fig,axes = plt.subplots(1,3,figsize=(12,5),sharex=True,sharey=True)
    if ix is None:
        for ii in range(w.shape[1]):
            axes[0].plot(w[:,ii,0], w[:,ii,1], marker=None)
            axes[1].plot(w[:,ii,0], w[:,ii,2], marker=None)
            axes[2].plot(w[:,ii,1], w[:,ii,2], marker=None)
    else:
        axes[0].plot(w[:,ix,0], w[:,ix,1], marker=None)
        axes[1].plot(w[:,ix,0], w[:,ix,2], marker=None)
        axes[2].plot(w[:,ix,1], w[:,ix,2], marker=None)

    axes[0].set_xlabel("X")
    axes[0].set_ylabel("Y")

    axes[1].set_xlabel("X")
    axes[1].set_ylabel("Z")

    axes[2].set_xlabel("Y")
    axes[2].set_ylabel("Z")
    fig.tight_layout()
    return fig

def sanders_nvecs(N_max, dx, dy, dz):
    from itertools import product
    NNx = range(-N_max, N_max+1, dx)
    NNy = range(-N_max, N_max+1, dy)
    NNz = range(-N_max, N_max+1, dz)
    n_vectors = np.array([[i,j,k] for (i,j,k) in product(NNx,NNy,NNz)
                          if(not(i==0 and j==0 and k==0)            # exclude zero vector
                             and (k>0                               # northern hemisphere
                                  or (k==0 and j>0)                 # half of x-y plane
                                  or (k==0 and j==0 and i>0))       # half of x axis
                             and np.sqrt(i*i+j*j+k*k)<=N_max)])     # inside sphere
    return n_vectors

def test_nvecs():
    nvecs = generate_n_vectors(N_max=6, dx=2, dy=2, dz=2)
    nvecs_sanders = sanders_nvecs(N_max=6, dx=2, dy=2, dz=2)

    assert np.all(nvecs == nvecs_sanders)

def test_compare_action_prepare():
    from ..actionangle import _action_prepare
    import solver
    logger.setLevel(logging.ERROR)
    AA = np.random.uniform(0., 100., size=(1000,6))

    A1,b1 = solver.solver(AA, N_max=6, symNx=2)
    A2,b2,n = _action_prepare(AA, N_max=6, dx=2, dy=2, dz=2)

    assert np.allclose(A1, A2)
    assert np.allclose(b1, b2)

def test_compare_angle_prepare():
    from ..actionangle import _angle_prepare
    import solver
    logger.setLevel(logging.ERROR)
    AA = np.random.uniform(0., 100., size=(1000,6))
    t = np.linspace(0., 100., 1000)

    A1,b1 = solver.angle_solver(AA, t, N_max=6, sign=1., symNx=2)
    A2,b2,n = _angle_prepare(AA, t, N_max=6, dx=2, dy=2, dz=2)

    # row = slice(None,None)
    # col = slice(None,None)
    # assert np.allclose(A1[row,col], A2[row,col])

    assert np.allclose(A1, A2)
    assert np.allclose(b1, b2)

class TestActions(object):

    def setup(self):
        self.usys = (u.kpc, u.Msun, u.Myr)
        self.potential = LM10Potential()
        acc = lambda t,x: self.potential.acceleration(x)
        self.integrator = LeapfrogIntegrator(acc)

    def test_box(self):
        return
        box_w0 = [-59.420, 53.435, -26.473, -0.1943, 0.0601, -0.1347]
        t,w = integrator.run(box_w0, dt=1., nsteps=15000)
        fig = plot_orbit(w,ix=0)
        fig.savefig(os.path.join(plot_path,"box.png"))
        actions,angles,nvecs = find_actions(t, w[:,0], N_max=6, usys=self.usys)

    def test_loop(self):
        N_max = 6

        loop_w0 = np.append(([14.69, 1.8, 0.12]*u.kpc).decompose(self.usys).value,
                            ([15.97, -128.9, 44.68]*u.km/u.s).decompose(self.usys).value)
        t,w = self.integrator.run(loop_w0, dt=0.5, nsteps=20000)

        w2 = w.copy()
        w2[:,0,3:] = (w2[:,0,3:]*u.kpc/u.Myr).to(u.km/u.s).value
        act,ang,n_vec,toy_aa,pars = genfunc_3d.find_actions(w2[:,0], t/1000., N_matrix=N_max)
        print(act[:3])
        print(ang[3:6])
        # return

        fig = plot_orbit(w,ix=0)
        fig.savefig(os.path.join(plot_path,"loop.png"))

        actions,angles,nvecs = find_actions(t, w[:,0], N_max=N_max, usys=self.usys)
        J = (actions[:3]*u.kpc**2/u.Myr).to(u.kpc*u.km/u.s)
        print(J)
        omega = (angles[3:6]/u.Myr).to(1/u.Gyr)
        print(omega)
        theta = (angles[:3,None] + angles[3:6,None]*t[np.newaxis]) % 2*np.pi

        return

        fig,axes = plt.subplots(1,2,sharex=True,sharey=True,figsize=(10,5))
        axes[0].plot(theta[0]/np.pi, theta[1]/np.pi, alpha=0.2, marker=None)
        axes[1].plot(theta[0]/np.pi, theta[2]/np.pi, alpha=0.2, marker=None)
        axes[0].set_xlim(0,2)
        axes[0].set_ylim(0,2)
        fig.savefig(os.path.join(plot_path,"loop_angles.png"))
