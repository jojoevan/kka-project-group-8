
"""Orienteering instance and O(n) route decoder."""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from src.data_prep import OPS_SCENARIO

def haversine_matrix(lat, lon):
    lat=np.radians(np.asarray(lat,float)); lon=np.radians(np.asarray(lon,float))
    dlat=lat[:,None]-lat[None,:]; dlon=lon[:,None]-lon[None,:]
    a=np.sin(dlat/2)**2+np.cos(lat[:,None])*np.cos(lat[None,:])*np.sin(dlon/2)**2
    return 6371.0088*2*np.arcsin(np.sqrt(np.clip(a,0,1)))

@dataclass
class Instance:
    names: list
    risk: np.ndarray
    ops: np.ndarray
    dist: np.ndarray
    depot: int=0
    speed: float=200.
    dwell: float=1.
    time_limit: float=72.  # Batas waktu misi (hours)
    g0: float=.01
    kappa: float=1.
    def evaluate(self, perm, details=False):
        t=0.; prev=self.depot; prize=0.; route=[]; seen=set()
        for raw in perm:
            i=int(raw)
            if i==self.depot or i in seen: continue
            leg=self.dist[prev,i]/self.speed
            return_leg=self.dist[i,self.depot]/self.speed
            if t+leg+self.dwell+return_leg > self.time_limit+1e-9: continue
            t += leg; arrival=t
            p=float(self.risk[i]*np.exp(-self.g0*(1+self.kappa*self.ops[i])*arrival))
            prize += p
            route.append({"index":i,"province":self.names[i],"arrival_h":arrival,"prize":p,"risk":float(self.risk[i])})
            t += self.dwell; prev=i; seen.add(i)
        seq=[self.depot]+[x["index"] for x in route]+[self.depot]
        total_dist=sum(self.dist[a,b] for a,b in zip(seq[:-1],seq[1:]))
        mission=t+(self.dist[prev,self.depot]/self.speed)
        if details:
            visited={x["index"] for x in route}
            return {"route":route,"fitness":prize,"distance_km":float(total_dist),"mission_time_h":float(mission),
                    "remaining_time_h":float(self.time_limit-mission),
                    "skipped":[{"province":self.names[i],"risk":float(self.risk[i])} for i in range(1,len(self.names)) if i not in visited]}
        return float(prize)

INSTANCE_SIZES=(6,10,15,25,38)
OPS_INSTANCE_SIZE=6  # the instance of provinces with operational data

def select_provinces(features, n, scenario="2026", depot_name="Riau"):
    """Province names for an instance of size n, depot first.

    n=6 is the depot plus the provinces with operational data; any other n is the depot plus the
    top n-1 by Risiko (ties broken by name), so n=38 is all provinces. The depot is always included
    and counts towards n, so a depot outside the operational set drops the lowest-Risiko one.
    """
    if not 2<=n<=len(features): raise ValueError(f"Ukuran instance {n} di luar rentang 2..{len(features)}")
    col=f"risk_{scenario}"
    if col not in features: raise ValueError(f"Skenario tahun {scenario} tidak tersedia")
    if depot_name not in set(features.Provinsi): raise ValueError(f"Depot {depot_name} tidak ada di data provinsi")
    ranked=features.assign(_neg=-features[col]).sort_values(["_neg","Provinsi"])
    others=ranked[ranked.Provinsi!=depot_name]
    if n==OPS_INSTANCE_SIZE: others=others[others.has_ops.astype(bool)]
    chosen=others.Provinsi.tolist()[:n-1]
    return [depot_name]+chosen

def build_instance(features, coords, n=38, scenario="2026", depot_name="Riau", speed=200, detour=1.15,
                   dwell=1, time_limit=72, g0=.01, kappa=1):
    """Instance over select_provinces(...); Risiko is taken as-is from data prep, never rescaled."""
    names=select_provinces(features,n,scenario,depot_name)
    f=features.set_index("Provinsi").loc[names].reset_index()
    f=f.merge(coords,on="Provinsi",how="left",validate="one_to_one")
    missing=f.loc[f.lat.isna()|f.lon.isna(),"Provinsi"].tolist()
    if missing: raise ValueError(f"Koordinat tidak ditemukan untuk: {missing}")
    dist=haversine_matrix(f.lat.to_numpy(),f.lon.to_numpy())*detour
    risk=f[f"risk_{scenario}"].to_numpy(float)
    # Operational severity speeds up decay only in the scenario it was observed in.
    ops=f["ops_norm"].to_numpy(float) if scenario==OPS_SCENARIO else np.zeros(len(f))
    return Instance(names,risk,ops,dist,0,speed,dwell,time_limit,g0,kappa)
