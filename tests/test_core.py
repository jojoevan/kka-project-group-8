
import numpy as np
from src.data_prep import parse_id_number, parse_pm25, parse_visibility
from src.instance import haversine_matrix, Instance
from src.algorithms.simulated_annealing import solve as sa
from src.algorithms.genetic_algorithm import solve as ga

def test_indonesian_number(): assert parse_id_number("1.284,70")==1284.70
def test_pm25_range(): assert parse_pm25("Sedang - Berbahaya")==4
def test_visibility_minimum(): assert parse_visibility("≤ 0.6 - 7")==0.6
def test_haversine_symmetry():
    d=haversine_matrix([0,1],[0,1]); assert np.allclose(d,d.T); assert d[0,0]==0
def test_decoder_budget():
    inst=Instance(["Depot","A","B"],np.array([0.,1.,.8]),np.zeros(3),np.array([[0,10,20],[10,0,10],[20,10,0]]),time_limit=1,speed=100,dwell=.1)
    out=inst.evaluate([1,2],True); assert out["mission_time_h"]<=inst.time_limit+1e-9
def test_algorithms_permutation():
    n=5; d=np.ones((n,n))*100; np.fill_diagonal(d,0)
    inst=Instance(list("abcde"),np.array([0,.9,.8,.7,.6]),np.zeros(n),d,time_limit=72)
    for fn in [sa,ga]:
        r=fn(inst,budget=30,seed=7)
        assert len(set(r["best_perm"]))==n-1
