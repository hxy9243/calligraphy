"""Repair local rail ownership at transverse intersections, before raster replay.

The same geometry-only rule is used for every character. The other strokes only
locate crossing intervals; they never clip or erase the reconstructed stroke.
"""
import copy
import cv2
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import map_coordinates, distance_transform_edt
from scipy.spatial import cKDTree
from .brush_grammar import complete

CONFIG={'crossingMargin':4,'intervalPadding':7,'maximumFraction':.58,
        'minimumSpan':5,'maximumTangentCosine':.88,'minimumGlyphIoU':.975,
        'maximumDisplacement':28,'terminalFraction':.12}


def _directions(a):
    p=a.mean(1)
    v=np.array([p[min(len(p)-1,k+3)]-p[max(0,k-3)] for k in range(len(p))])
    return p,v/np.maximum(np.linalg.norm(v,axis=1,keepdims=True),1e-8)


def repair_crossings(strokes, *, preserve_corners=False, inferred_corners=False):
    result=copy.deepcopy(strokes)
    if len(strokes) < 2:
        return result, []
    masks=[complete(s) for s in strokes]
    original=np.maximum.reduce(masks)>.5
    trees=[]
    for s in strokes:
        p,v=_directions(np.asarray(s['contacts']))
        trees.append((cKDTree(p),v))
    reports=[]
    for index,stroke in enumerate(strokes):
        a=np.asarray(stroke['contacts'],float);n=len(a)
        if n<8:continue
        _,direction=_directions(a)
        candidate=a.copy();edits=[];changed_stations=set()
        for rail in [0,1]:
            p=a[:,rail];arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
            length=arc[-1]
            hidden=np.zeros(n,bool)
            for j,mask in enumerate(masks):
                if j==index:continue
                near=cv2.dilate(np.uint8(mask>.2),np.ones((9,9),np.uint8))
                overlaps=map_coordinates(near.astype(float),[p[:,1],p[:,0]],order=0,mode='constant')>.5
                _,nearest=trees[j][0].query(p)
                transverse=np.abs(np.sum(direction*trees[j][1][nearest],axis=1))<CONFIG['maximumTangentCosine']
                hidden|=overlaps&transverse
            protected=(arc<CONFIG['terminalFraction']*length)|(arc>(1-CONFIG['terminalFraction'])*length)
            hidden[protected]=False
            # Expand by physical arc length rather than by irregular control count.
            padding = 20 if inferred_corners else CONFIG['intervalPadding']
            expanded=np.array([np.any(hidden & (np.abs(arc-x)<=padding)) for x in arc])
            expanded[protected]=False
            bounds=np.flatnonzero(np.diff(np.r_[False,expanded,False])).reshape(-1,2)
            for start,stop in bounds:
                lo=max(1,start-1);hi=min(n-2,stop)
                if inferred_corners:
                    # An interval edge can itself land on a fitted bump corner.
                    # Move to its outside shoulder before choosing interpolation anchors.
                    tags = set(stroke.get('corners', []))
                    while lo > 1 and (lo in tags or lo + 1 in tags):
                        lo -= 1
                    while hi < n - 2 and (hi in tags or hi - 1 in tags):
                        hi += 1
                if hi-lo<2 or (arc[hi]-arc[lo])>CONFIG['maximumFraction']*length:continue
                # An authored entry/exit shoulder is not an overlap artifact.
                # Protect it even when the broad centerline barely changes angle.
                marked = any(lo<=k<=hi for k in stroke.get('corners', []))
                # Fitted corner tags include contour notches. Only relax them
                # when both ends describe the same straight body direction.
                centers = a.mean(1)
                chord_center = centers[hi] - centers[lo]
                chord_length = np.linalg.norm(chord_center)
                normal = np.array([-chord_center[1], chord_center[0]]) / max(chord_length, 1e-8)
                body_deviation = np.max(np.abs((centers[lo:hi+1] - centers[lo]) @ normal))
                straight_inferred = (inferred_corners and np.dot(direction[lo], direction[hi]) > .95
                                     and body_deviation < min(8, .12 * chord_length))
                if marked and not straight_inferred and any(
                    lo<=k<=hi and (preserve_corners or arc[k]<.25*length or arc[k]>.8*length)
                    for k in stroke.get('corners', [])):continue
                chord=p[hi]-p[lo];axis=int(np.argmax(abs(chord)));other=1-axis
                span=abs(chord[axis])
                if span<CONFIG['minimumSpan']:continue
                sign=np.sign(chord[axis]);xs=sign*p[lo:hi+1,axis]
                if np.any(np.diff(xs)<-1.5):continue
                # Genuine turns must remain turns; only interpolate a local body run.
                if abs(np.dot(direction[lo],direction[hi]))<.55:continue
                anchor_ids=[max(0,lo-2),lo,hi,min(n-1,hi+2)]
                ax=sign*p[anchor_ids,axis];ay=p[anchor_ids,other]
                keep=np.r_[True,np.diff(ax)>.05];ax=ax[keep];ay=ay[keep]
                if len(ax)<2 or np.any(np.diff(ax)<=0):continue
                fit=PchipInterpolator(ax,ay,extrapolate=False)
                values=fit(np.clip(xs,ax[0],ax[-1]))
                delta=values-p[lo:hi+1,other]
                if not np.isfinite(values).all() or np.max(abs(delta))>CONFIG['maximumDisplacement']:continue
                if np.max(abs(delta))<1:continue
                candidate[lo:hi+1,rail,other]=values
                changed_stations.update(range(lo+1,hi))
                edits.append({'rail':rail,'range':[int(lo),int(hi)],'axis':axis,'maxDisplacement':float(np.max(abs(delta)))})
        if not edits:continue
        candidate[:2]=a[:2];candidate[-2:]=a[-2:]
        proposal=copy.deepcopy(stroke);proposal['contacts']=candidate.tolist()
        proposal['corners']=[k for k in stroke.get('corners',[]) if k not in changed_stations]
        proposal['features']=[f for f in stroke.get('features',[]) if f['station'] not in changed_stations]
        pmask=complete(proposal)
        others=np.maximum.reduce([m for j,m in enumerate(masks) if j!=index])
        new_union=np.maximum(others,pmask)>.5
        score=float(np.count_nonzero(new_union&original)/max(1,np.count_nonzero(new_union|original)))
        before_components=cv2.connectedComponents(np.uint8(masks[index]>.5))[0]
        after_components=cv2.connectedComponents(np.uint8(pmask>.5))[0]
        accepted=score>=CONFIG['minimumGlyphIoU'] and before_components==after_components
        if accepted:result[index]=proposal
        reports.append({'stroke':index+1,'accepted':accepted,'glyphRetentionIoU':score,'edits':edits,
                        'endpointsPreserved':bool(np.array_equal(candidate[[0,1,-2,-1]],a[[0,1,-2,-1]]))})
    # Short internal bars use one centerline and width; they must not inherit
    # either support's silhouette. This classification contains no character IDs.
    for index,stroke in enumerate([] if preserve_corners else strokes):
        a=np.asarray(stroke['contacts']);p=a.mean(1);chord=p[-1]-p[0]
        length=np.linalg.norm(chord)
        if length<40:continue
        tangent=chord/length;normal=np.array([-tangent[1],tangent[0]])
        arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
        half=np.abs((a[:,1]-a[:,0])@normal)/2
        body=(arc>.18*arc[-1])&(arc<.82*arc[-1])
        width=float(np.median(half[body])) if body.any() else 0
        if width<3 or np.max(half)>width*1.6 or arc[-1]/length>1.17:continue
        if np.max(np.abs((p-p[0])@normal))>9:continue
        other=np.maximum.reduce([m for j,m in enumerate(masks) if j!=index])
        near=cv2.dilate(np.uint8(other>.2),np.ones((13,13),np.uint8))
        if not all(map_coordinates(near.astype(float),[p[[0,-1],1],p[[0,-1],0]],order=0)>.5):continue
        contacts=[]
        for u,w in [(0,0),(.08,width),(.5,width),(.92,width),(1,0)]:
            center=p[0]+u*chord;contacts.append([center-normal*w,center+normal*w])
        proposal=copy.deepcopy(result[index]);proposal.update(contacts=np.asarray(contacts).tolist(),corners=[],features=[],tension=.5)
        candidate_union=np.maximum(other,complete(proposal))>.5
        retention=float(np.count_nonzero(candidate_union&original)/np.count_nonzero(candidate_union|original))
        if retention>=CONFIG['minimumGlyphIoU']:
            result[index]=proposal
            reports.append({'stroke':index+1,'accepted':True,'kind':'straight-internal-body','glyphRetentionIoU':retention,'edits':[],'endpointsPreserved':True})
    # Hidden tip overlaps are part of the model. Moving host edges without
    # restoring these overlaps can open seams in the final union.
    repaired_masks=[complete(s) for s in result]
    for index,stroke in enumerate([] if preserve_corners else result):
        a=np.asarray(stroke['contacts']);p=a.mean(1);changed=False
        tip_arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
        head_neighbor=int(np.searchsorted(tip_arc,.2*tip_arc[-1]))
        tail_neighbor=int(np.searchsorted(tip_arc,.8*tip_arc[-1]))
        for endpoint,neighbor in [(0,head_neighbor),(-1,tail_neighbor)]:
            raw=np.asarray(strokes[index]['contacts']).mean(1)[endpoint]
            direction=p[endpoint]-p[neighbor];direction/=max(np.linalg.norm(direction),1e-8)
            for j,mask in enumerate(masks):
                if j==index:continue
                if np.count_nonzero((masks[index]>.5)&(mask>.5))<8:continue
                near=cv2.dilate(np.uint8(mask>.2),np.ones((13,13),np.uint8))
                if map_coordinates(near.astype(float),[[raw[1]],[raw[0]]],order=0)[0]<.5:continue
                distance=distance_transform_edt(repaired_masks[j]>.5)
                steps=np.linspace(0,26,105);points=p[endpoint]+steps[:,None]*direction
                depths=map_coordinates(distance,[points[:,1],points[:,0]],order=1,mode='constant')
                good=np.flatnonzero(depths>=4)
                if not len(good) or good[0]==0:continue
                delta=direction*steps[good[0]]
                arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))];u=arc/max(arc[-1],1)
                weight=np.clip((.25-u)/.25,0,1) if endpoint==0 else np.clip((u-.75)/.25,0,1)
                a+=weight[:,None,None]*delta;changed=True
                reports.append({'stroke':index+1,'accepted':True,'kind':'hidden-join-extension','supportStroke':j+1,'end':int(endpoint),'pixels':float(np.linalg.norm(delta)),'edits':[],'endpointsPreserved':False})
                break
        if changed:stroke['contacts']=a.tolist()
    # Repair proposals are coupled: accepting each against old neighbors is not
    # sufficient. Preserve the original overlap graph after all simultaneous edits.
    for _ in range(len(strokes)):
        final_masks=[complete(s)>.5 for s in result];rolled_back=False
        for i in range(len(strokes)):
            for j in range(i+1,len(strokes)):
                old_overlap=int(np.count_nonzero((masks[i]>.5)&(masks[j]>.5)))
                overlap=int(np.count_nonzero(final_masks[i]&final_masks[j]))
                if old_overlap<8 or overlap>=max(4,old_overlap*.35):continue
                choices=[]
                for k,l in [(i,j),(j,i)]:
                    restored=masks[k]>.5
                    if np.count_nonzero(restored&final_masks[l])>=max(4,old_overlap*.35):
                        choices.append((int(np.count_nonzero(restored!=final_masks[k])),k))
                indices=[min(choices)[1]] if choices else [i,j]
                for k in indices:
                    result[k]=copy.deepcopy(strokes[k]);final_masks[k]=masks[k]>.5
                    for r in reports:
                        if r['stroke']==k+1:r['accepted']=False;r['reason']='coupled-overlap-guard'
                rolled_back=True
        if not rolled_back:break
    final=np.maximum.reduce([complete(s) for s in result])>.5
    if cv2.connectedComponents(np.uint8(final))[0]!=cv2.connectedComponents(np.uint8(original))[0]:
        for r in reports:r['accepted']=False;r['reason']='whole-glyph-topology-guard'
        return copy.deepcopy(strokes),reports
    return result,reports


def smooth_kai_program(program, targets=None, *, inferred_corners=False):
    """Repair crossing-local rail defects, retaining Kai corners and terminals.

    Returns a fresh program and evidence. The complete proposal is rejected if
    coupled glyph retention, normalized bounds, sampled motion, or optional
    original-target fitting gates fail. Timing and input provenance are retained.
    """
    from .stroke_ir import compile_program, validate_program, SCHEMA_VERSION
    from .stroke_fitting import _motion_checks, _iou

    validate_program(program)
    if program['schemaVersion'] != SCHEMA_VERSION:
        raise ValueError('crossing smoothing requires paired-contact IR 0.2')
    before = compile_program(program)
    records, edits = repair_crossings(before, preserve_corners=True, inferred_corners=inferred_corners)
    result = copy.deepcopy(program)
    evidence = {'method': 'crossing-rails-kai/1', 'edits': edits, 'strokes': [], 'minimumTargetIoU': .90}
    rejected = None
    if targets is not None and len(targets) != len(records):
        raise ValueError('one target mask is required per stroke')
    for i, (old, record, output) in enumerate(zip(before, records, result['strokes'])):
        stations = np.asarray(record['contacts']) / 480
        if not np.isfinite(stations).all() or np.any((stations < 0) | (stations > 1)):
            rejected = 'normalized-bounds'
        changed = record['contacts'] != old['contacts']
        motion = _motion_checks(record) if changed else None
        if motion and not (motion['monotonic'] and motion['prefixConnected']):
            rejected = 'sampled-motion'
        score = _iou(complete(record), np.asarray(targets[i]) > .5) if targets is not None else None
        if score is not None and score < .90:
            rejected = 'original-target-fit'
        if changed:
            output['geometry'].update(stations=stations.tolist(), corners=record.get('corners', []),
                                      tension=record.get('tension', 0))
        evidence['strokes'].append({'id': output['id'], 'changed': changed,
                                    'motion': motion, 'targetIoU': score})
    old_union = np.maximum.reduce([complete(s) for s in before])
    new_union = np.maximum.reduce([complete(s) for s in records])
    evidence['glyphRetentionIoU'] = _iou(new_union, old_union > .5)
    if evidence['glyphRetentionIoU'] < CONFIG['minimumGlyphIoU']:
        rejected = 'combined-glyph-retention'
    evidence['accepted'] = rejected is None
    evidence['reason'] = rejected
    if rejected:
        result = copy.deepcopy(program)
        for edit in edits:
            edit['accepted'] = False
            edit['reason'] = rejected
        for stroke in evidence['strokes']:
            stroke['changed'] = False
    result['provenance']['crossingSmoothing'] = evidence
    validate_program(result)
    return result, evidence


def smooth_kai_contacts(strokes, *, inferred_corners=False):
    """Clean fitted Kai contacts, preserving scheduled strokes and major pieces.

    Tiny satellite pieces below 1% of their stroke and 128 canonical pixels are
    fitting debris. Whole dots and substantial disconnected components survive.
    Removed satellites are reported, never silently merged into another stroke.
    """
    from .contact_stroke import complete_stroke
    from .stroke_fitting import _motion_checks, _iou

    source = copy.deepcopy(strokes)
    clean = copy.deepcopy(strokes)
    removed = []
    for i, stroke in enumerate(clean):
        if 'segments' not in stroke:
            continue
        areas = [int(np.count_nonzero(complete(s['stroke']) > .5)) for s in stroke['segments']]
        largest = max(areas)
        keep = []
        for j, (segment, area) in enumerate(zip(stroke['segments'], areas)):
            if area <= 128 and area < .01 * largest:
                removed.append({'stroke': i + 1, 'segment': j + 1, 'pixels': area})
            else:
                keep.append(segment)
        stroke['segments'] = keep
    flat, locations = [], []
    for i, stroke in enumerate(clean):
        if 'segments' in stroke:
            for j, segment in enumerate(stroke['segments']):
                flat.append(segment['stroke']); locations.append((i, j))
        else:
            flat.append(stroke); locations.append((i, None))
    fixed, edits = repair_crossings(flat, preserve_corners=True, inferred_corners=inferred_corners)
    result = copy.deepcopy(clean)
    reason, motion = None, []
    for old, new, (i, j) in zip(flat, fixed, locations):
        check = _motion_checks(new) if old['contacts'] != new['contacts'] else None
        motion.append(check)
        if check and not (check['monotonic'] and check['prefixConnected']):
            reason = 'sampled-motion'
        if j is None:
            result[i] = new
        else:
            result[i]['segments'][j]['stroke'] = new
    before = np.maximum.reduce([complete_stroke(s) for s in source])
    after = np.maximum.reduce([complete_stroke(s) for s in result])
    retention = _iou(after, before > .5)
    if retention < .975:
        reason = 'combined-glyph-retention'
    if reason:
        result = source
    report = {'method': 'crossing-rails-kai/2', 'accepted': reason is None, 'reason': reason,
              'glyphRetentionIoU': retention, 'edits': edits, 'componentMotionChecks': motion,
              'removedSatellites': removed if reason is None else [],
              'strokes': [{'changed': a != b} for a, b in zip(source, result)]}
    return result, report
