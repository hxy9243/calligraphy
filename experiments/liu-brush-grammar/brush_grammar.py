"""Experimental asymmetric contact-strip brush, with explicitly authored gestures.

Pairs of boundary landmarks specify a brush contact cross-section. Its angle is
independent of travel direction, so entry cuts, shoulders and folds survive.
Successive contact strips deposit vector polygons; the renderer never sees the
reference image. This is a geometric brush model, not a bristle simulation.
"""
import cv2
import numpy as np
from scipy.interpolate import CubicHermiteSpline
from scipy.ndimage import distance_transform_edt, map_coordinates
from scipy.optimize import least_squares


def validate(stroke):
    a = np.asarray(stroke['contacts'], float)
    if a.ndim != 3 or a.shape[1:] != (2, 2) or len(a) < 3 or not np.isfinite(a).all():
        raise ValueError('Expected at least three finite pairs of [x,y] boundary points')
    if np.linalg.norm(np.diff(a.mean(1), axis=0), axis=1).sum() < 1:
        raise ValueError('A gesture must travel')
    return a


def sample(stroke, per_span=16):
    a = validate(stroke)
    t = np.arange(len(a), dtype=float)
    # Explicit corner landmarks have zero tangents. No smoothing across a fold.
    tangent = np.gradient(a, axis=0) * stroke.get('tension', .65)
    for k in stroke.get('corners', []):
        tangent[k] = 0
    u = np.linspace(0, len(a)-1, (len(a)-1)*per_span+1)
    rails = CubicHermiteSpline(t, a, tangent, axis=0)(u)
    center = rails.mean(1)
    arc = np.linalg.norm(np.diff(center, axis=0), axis=1)
    width = np.linalg.norm(rails[:, 1]-rails[:, 0], axis=1)
    cost = np.maximum(arc, .12) * (1+.2*width[1:]/max(np.median(width),1))
    for feature in stroke.get('features', []):
        k = feature['station']
        if feature['kind'] in ('entry-press','square-fold','finish-press','hook-turn'):
            cost *= 1 + 1.8*np.exp(-((u[1:]-k)/.55)**2)
    times = np.r_[0, np.cumsum(cost)]
    times = .025+.95*times/times[-1]
    return rails, times


class ContactBrush:
    """Monotonic deposition of overlapping contact strips, with subpixel edges."""
    def __init__(self, stroke, size=480, scale=3):
        self.rails,self.times = sample(stroke)
        self.size,self.scale = size,scale
        self.canvas = np.zeros((size*scale,size*scale),np.uint8)
        self.cursor = 0
        self.progress = 0.

    def advance(self, progress):
        if not np.isfinite(progress) or progress < self.progress:
            raise ValueError('Progress must be finite and monotonic')
        self.progress = progress
        stop = np.searchsorted(self.times,np.clip(progress,0,1),side='right')
        for k in range(max(1,self.cursor),stop):
            # Non-convex folds are legal: fillPoly, never fillConvexPoly.
            p = self.rails[[k-1,k]][:, [0,1]]
            q = np.array([p[0,0],p[1,0],p[1,1],p[0,1]])
            cv2.fillPoly(self.canvas,[np.round(q*self.scale*16).astype(np.int32)],255,shift=4)
        self.cursor = stop
        return cv2.resize(self.canvas,(self.size,self.size),interpolation=cv2.INTER_AREA).astype(np.float32)/255


def complete(stroke):
    return ContactBrush(stroke).advance(1)


def fit_strokes(strokes, target, bound=7.):
    """Bounded reference fitting; inferred hidden crossing edges stay authored.

    Only initially visible contour samples follow the target signed distance.
    Nearby stroke interiors are excluded, retaining full overlapping strokes.
    Displacement and change-of-curvature penalties keep the gesture stable.
    """
    import copy
    initial = [complete(s) for s in strokes]
    mask = target > .5
    sdf = distance_transform_edt(~mask)-distance_transform_edt(mask)
    fitted, reports = [], []
    for i,s in enumerate(strokes):
        a = validate(s)
        other = np.maximum.reduce([v for j,v in enumerate(initial) if j!=i]) if len(strokes)>1 else np.zeros_like(target)
        # Avoid pulling invisible overlap edges onto the outside of the glyph.
        other = cv2.dilate((other>.5).astype(np.uint8),np.ones((9,9),np.uint8))
        points,_ = sample(s,8)
        weight = 1-map_coordinates(other.astype(float),points.reshape(-1,2).T[::-1],order=1,mode='constant')
        weight = weight.reshape(points.shape[:2])
        tips = np.linalg.norm(a[:,0]-a[:,1],axis=1) < 1e-6
        def decode(flat):
            contacts=flat.reshape(a.shape).copy()
            contacts[tips]=contacts[tips].mean(1,keepdims=True)
            return contacts
        def residual(flat):
            candidate=copy.deepcopy(s);candidate['contacts']=decode(flat).tolist()
            points,_=sample(candidate,8)
            boundary=map_coordinates(sdf,points.reshape(-1,2).T[::-1],order=1,mode='nearest').reshape(points.shape[:2])
            delta=flat.reshape(a.shape)-a
            return np.r_[(boundary*weight).ravel(),.22*delta.ravel(),.32*np.diff(delta,n=2,axis=0).ravel()]
        result=least_squares(residual,a.ravel(),bounds=((a-bound).ravel(),(a+bound).ravel()),max_nfev=45,ftol=1e-4)
        fitted_s=copy.deepcopy(s);fitted_s['contacts']=decode(result.x).tolist()
        fitted.append(fitted_s)
        reports.append(dict(stroke=i+1,max_landmark_displacement=float(np.abs(result.x-a.ravel()).max()),cost=float(result.cost),evaluations=result.nfev))
    return fitted,reports
