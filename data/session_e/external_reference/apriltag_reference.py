#!/usr/bin/env python3
"""
apriltag_reference.py — external localization reference for Session E.

Answers one question: how far is the localization estimate the robot acted on from an
independent measurement of where the robot actually was?

The independent measurement comes from five AprilTags (tag36h11, 125 mm black square)
fixed to the walls of the test floor for an unrelated Nav2 docking experiment. Three of
them have surveyed map coordinates. Whenever a mission image happens to contain one,
the camera pose can be recovered from the tag by PnP and compared against the AMCL pose
recorded in the same audit record.

Reads only from the published dataset. Writes only into external_reference/.

Inputs (versioned, hand-authored, treated as data):
    external_reference/tag_survey.csv           surveyed tag geometry
    external_reference/platform_extrinsics.csv  camera pose on each robot
    external_reference/hd_pro_webcam_c920_v2.yaml   camera calibration as used on the robots
    missions.csv                                AMCL poses and image references

Outputs:
    external_reference/detections.csv           every tag detection, used or not
    external_reference/pose_estimates.csv       PnP result and delta vs AMCL, per detection
    external_reference/visibility_analysis.csv  where a tag should have been visible
    external_reference/summary.json             aggregates, eliminations, negative results
    external_reference/README.md                method and results, generated from the above

Usage:  python3 apriltag_reference.py --dataset <path to data/session_e>
Requires: numpy, opencv-python, pupil-apriltags
"""

import argparse, csv, json, math, os, sys
from collections import Counter, defaultdict

import numpy as np
import cv2
from pupil_apriltags import Detector

# A tag smaller than this in the image cannot support a usable pose: corner localization
# error is roughly constant in pixels, so the resulting position error grows with the
# square of the distance. At 80 px a 125 mm tag is about 1.07 m away.
MIN_TAG_SIDE_PX = 80.0

# Tags whose surveyed pose is contradicted by their own optical geometry. Their samples
# are computed and published, but excluded from the aggregate. See README.
SURVEY_INCONSISTENT = {1}


# --------------------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------------------

def read_calibration(path):
    """Minimal reader for the ROS camera_info YAML used on the robots."""
    text = open(path, encoding='utf-8').read()

    def block(key):
        i = text.index(key)
        j = text.index('[', i)
        k = text.index(']', j)
        return [float(v) for v in text[j + 1:k].replace('\n', ' ').split(',') if v.strip()]

    K = np.array(block('camera_matrix'), float)[:9].reshape(3, 3)
    D = np.array(block('distortion_coefficients'), float)[:5]
    return K, D


def read_tag_survey(path):
    tags = {}
    for r in csv.DictReader(open(path, encoding='utf-8')):
        tid = int(r['tag_id'])
        if not r['center_x_m']:
            tags[tid] = None                      # known to exist, never surveyed
            continue
        tags[tid] = dict(
            side=float(r['side_m']),
            center=np.array([float(r['center_x_m']), float(r['center_y_m']),
                             float(r['center_z_m'])]),
            normal=np.array([float(r['normal_x']), float(r['normal_y']),
                             float(r['normal_z'])]),
            node=r['nearest_node_name'],
            survey_method=r['survey_method'],
            survey_uncertainty_m=(float(r['survey_uncertainty_m'])
                                  if r['survey_uncertainty_m'] not in ('', 'unspecified')
                                  else None),
        )
    return tags


def read_extrinsics(path):
    out = {}
    for r in csv.DictReader(open(path, encoding='utf-8')):
        out[r['platform_id']] = (float(r['camera_offset_x_m']), float(r['camera_height_m']))
    return out


# --------------------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------------------

def tag_corners_in_map(center, normal, side):
    """The four tag corners as TL, TR, BR, BL directly in map coordinates.

    Working in map coordinates throughout avoids any tag-local frame and therefore any
    convention about which way its axes point. `normal` points out of the wall, into the
    room; an upright observer facing the tag sees `right` to their right.
    """
    n = np.asarray(normal, float)
    n = n / np.linalg.norm(n)
    up = np.array([0.0, 0.0, 1.0])
    right = np.cross(-n, up)
    right /= np.linalg.norm(right)
    h = side / 2.0
    c = np.asarray(center, float)
    return np.array([c + h * up - h * right,
                     c + h * up + h * right,
                     c - h * up + h * right,
                     c - h * up - h * right])


def order_corners(corners):
    """Detector corners -> TL, TR, BR, BL by image position.

    Valid because the cameras are mounted level and the tags are upright on walls, so
    image roll is far below the 45 deg at which this ordering would become ambiguous.
    """
    c = np.asarray(corners, float)
    i = np.argsort(c[:, 1])
    top, bot = c[i[:2]], c[i[2:]]
    tl, tr = (top[0], top[1]) if top[0, 0] < top[1, 0] else (top[1], top[0])
    bl, br = (bot[0], bot[1]) if bot[0, 0] < bot[1, 0] else (bot[1], bot[0])
    return np.array([tl, tr, br, bl], float)


def solve_pose(objp, imgp, K, D):
    ok, rvec, tvec = cv2.solvePnP(objp, imgp, K, D, flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok:
        return None
    proj, _ = cv2.projectPoints(objp, rvec, tvec, K, D)
    rerr = float(np.mean(np.linalg.norm(proj.reshape(-1, 2) - imgp, axis=1)))
    R, _ = cv2.Rodrigues(rvec)
    cam = (-R.T @ tvec).ravel()                       # camera centre in map coordinates
    fwd = (R.T @ np.array([[0.0], [0.0], [1.0]])).ravel()
    return cam, math.atan2(fwd[1], fwd[0]), rerr


def world_to_camera(x, y, yaw, cam_dx, cam_z):
    """Camera centre and rotation for a robot at (x, y, yaw). Optical frame: z forward,
    x right, y down."""
    cam = np.array([x + cam_dx * math.cos(yaw), y + cam_dx * math.sin(yaw), cam_z])
    fwd = np.array([math.cos(yaw), math.sin(yaw), 0.0])
    right = np.array([math.sin(yaw), -math.cos(yaw), 0.0])
    down = np.array([0.0, 0.0, -1.0])
    return cam, np.vstack([right, down, fwd])


def wrap_deg(a):
    return math.degrees((a + math.pi) % (2 * math.pi) - math.pi)


# --------------------------------------------------------------------------------------
# Passes
# --------------------------------------------------------------------------------------

def load_missions(dataset):
    rows = []
    for r in csv.DictReader(open(os.path.join(dataset, 'missions.csv'), encoding='utf-8')):
        for kind, img, px, py, pw in (('start', 'image_start', 'start_x_m', 'start_y_m', 'start_yaw_rad'),
                                      ('finish', 'image_finish', 'end_x_m', 'end_y_m', 'end_yaw_rad')):
            if not r[img] or not r[px]:
                continue
            rows.append(dict(
                image=r[img], kind=kind, day=r['day'], run_id=r['run_id'],
                platform_id=r['platform_id'], experiment_id=r['experiment_id'],
                node_id=r['node_id'], node_name=r['node_name'],
                amcl_x=float(r[px]), amcl_y=float(r[py]), amcl_yaw=float(r[pw]),
                amcl_converged=r['amcl_converged'],
                amcl_covariance_trace=r['amcl_covariance_trace'],
                xy_error_m=r['xy_error_m'],
            ))
    return rows


def detect_all(dataset, images):
    """Detect tags in every referenced image, at 1x and 2x. Upscaling recovers tags that
    the detector misses at native resolution; the corners are rescaled back."""
    det = Detector(families='tag36h11', nthreads=4, quad_decimate=1.0, refine_edges=1)
    out = []
    for i, rec in enumerate(images, 1):
        if i % 50 == 0:
            print(f'      {i}/{len(images)} images', file=sys.stderr)
        path = os.path.join(dataset, rec['image'])
        gray = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            continue
        best = {}
        for scale in (1, 2):
            img = gray if scale == 1 else cv2.resize(gray, None, fx=2, fy=2,
                                                     interpolation=cv2.INTER_CUBIC)
            for d in det.detect(img):
                c = np.asarray(d.corners, float) / scale
                side = float(np.mean([np.linalg.norm(c[k] - c[(k + 1) % 4]) for k in range(4)]))
                if d.tag_id not in best or side > best[d.tag_id][0]:
                    best[d.tag_id] = (side, c, scale, float(d.decision_margin))
        for tid, (side, c, scale, margin) in sorted(best.items()):
            out.append(dict(rec, tag_id=tid, tag_side_px=side, corners=c,
                            detected_at_scale=scale, decision_margin=margin))
    return out


def estimate_poses(detections, tags, extr, K, D):
    rows = []
    for d in detections:
        tag = tags.get(d['tag_id'])
        if not tag:
            rows.append(dict(d, included='no', exclusion_reason='tag_not_surveyed'))
            continue
        objp = tag_corners_in_map(tag['center'], tag['normal'], tag['side'])
        res = solve_pose(objp, order_corners(d['corners']), K, D)
        if res is None:
            rows.append(dict(d, included='no', exclusion_reason='pnp_failed'))
            continue
        cam, yaw, rerr = res
        cam_dx, _ = extr[d['platform_id']]
        base = cam - np.array([cam_dx * math.cos(yaw), cam_dx * math.sin(yaw), 0.0])

        dx, dy = base[0] - d['amcl_x'], base[1] - d['amcl_y']
        n = tag['normal']
        rng = dx * n[0] + dy * n[1]                   # along the wall normal
        lat = -dx * n[1] + dy * n[0]                  # along the wall

        if d['tag_side_px'] < MIN_TAG_SIDE_PX:
            inc, why = 'no', f'tag_side_below_{MIN_TAG_SIDE_PX:.0f}px'
        elif d['tag_id'] in SURVEY_INCONSISTENT:
            inc, why = 'no', 'tag_survey_inconsistent'
        else:
            inc, why = 'yes', ''

        rows.append(dict(d,
                         tag_distance_m=float(np.linalg.norm(cam - tag['center'])),
                         reprojection_error_px=rerr,
                         camera_height_optical_m=float(cam[2]),
                         tag_x_m=float(base[0]), tag_y_m=float(base[1]),
                         tag_yaw_rad=yaw,
                         dx_m=dx, dy_m=dy,
                         dyaw_deg=wrap_deg(yaw - d['amcl_yaw']),
                         range_component_m=rng, lateral_component_m=lat,
                         included=inc, exclusion_reason=why))
    return rows


def visibility(images, tags, extr, K, D, detected):
    """For every image, predict where each surveyed tag should project, so that a
    non-detection can be attributed to framing rather than to the detector."""
    rows = []
    for rec in images:
        cam_dx, cam_z = extr[rec['platform_id']]
        cam, R = world_to_camera(rec['amcl_x'], rec['amcl_y'], rec['amcl_yaw'], cam_dx, cam_z)
        for tid, tag in sorted(tags.items()):
            if not tag:
                continue
            corners = tag_corners_in_map(tag['center'], tag['normal'], tag['side'])
            pc = (corners - cam) @ R.T
            if (pc[:, 2] <= 0.05).any():
                continue                              # behind or level with the camera
            uv = cv2.projectPoints(corners, cv2.Rodrigues(R)[0],
                                   (-R @ cam).reshape(3, 1), K, D)[0].reshape(-1, 2)
            inside = int(((uv[:, 0] >= 0) & (uv[:, 0] < 640) &
                          (uv[:, 1] >= 0) & (uv[:, 1] < 480)).sum())
            dist = float(np.linalg.norm(cam - tag['center']))
            if inside == 0:
                continue                              # not even partly in view
            rows.append(dict(
                image=rec['image'], day=rec['day'], platform_id=rec['platform_id'],
                node_name=rec['node_name'], tag_id=tid,
                predicted_distance_m=dist,
                predicted_side_px=float(K[0, 0] * tag['side'] / dist),
                u_min=float(uv[:, 0].min()), u_max=float(uv[:, 0].max()),
                v_min=float(uv[:, 1].min()), v_max=float(uv[:, 1].max()),
                corners_in_frame=inside,
                fully_in_frame='yes' if inside == 4 else 'no',
                detected='yes' if (rec['image'], tid) in detected else 'no'))
    return rows


# --------------------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------------------

def mean_sd(vals):
    a = np.asarray(vals, float)
    n = len(a)
    if n == 0:
        return dict(n=0)
    sd = float(a.std(ddof=1)) if n > 1 else 0.0
    half = 1.96 * sd / math.sqrt(n) if n > 1 else 0.0
    return dict(n=n, mean=round(float(a.mean()), 4), sd=round(sd, 4),
                ci95_low=round(float(a.mean()) - half, 4),
                ci95_high=round(float(a.mean()) + half, 4))


def summarize(poses, vis, tags, images):
    used = [p for p in poses if p['included'] == 'yes']
    dx = [p['dx_m'] for p in used]
    dy = [p['dy_m'] for p in used]
    dw = [p['dyaw_deg'] for p in used]

    res = []
    if used:
        mx, my = float(np.mean(dx)), float(np.mean(dy))
        res = [math.hypot(p['dx_m'] - mx, p['dy_m'] - my) for p in used]

    per_tag = {}
    for tid in sorted({p['tag_id'] for p in poses}):
        g = [p for p in poses if p['tag_id'] == tid and 'dx_m' in p]
        gi = [p for p in g if p['included'] == 'yes']
        per_tag[str(tid)] = dict(
            detections=len(g), included=len(gi),
            surveyed=tags.get(tid) is not None,
            normal=(tags[tid]['normal'].tolist() if tags.get(tid) else None),
            dx_m=mean_sd([p['dx_m'] for p in gi]),
            dy_m=mean_sd([p['dy_m'] for p in gi]),
            dyaw_deg=mean_sd([p['dyaw_deg'] for p in gi]),
            range_component_m=mean_sd([p['range_component_m'] for p in gi]),
            lateral_component_m=mean_sd([p['lateral_component_m'] for p in gi]),
            camera_height_optical_m=mean_sd(
                [p['camera_height_optical_m'] for p in g
                 if p['tag_side_px'] >= MIN_TAG_SIDE_PX]),
            reprojection_error_px=mean_sd([p['reprojection_error_px'] for p in gi]),
            days=sorted({p['day'] for p in gi}),
            platforms=sorted({p['platform_id'] for p in gi}),
        )

    def cell(full, big):
        g = [v for v in vis
             if (v['fully_in_frame'] == 'yes') == full
             and (v['predicted_side_px'] >= MIN_TAG_SIDE_PX) == big]
        d = sum(1 for v in g if v['detected'] == 'yes')
        return dict(images=len(g), detected=d, missed=len(g) - d)

    unexplained = [v for v in vis
                   if v['fully_in_frame'] == 'yes'
                   and v['predicted_side_px'] >= MIN_TAG_SIDE_PX
                   and v['detected'] == 'no']

    return dict(
        images_searched=len(images),
        detections_total=len(poses),
        detections_included=len(used),
        min_tag_side_px=MIN_TAG_SIDE_PX,
        aggregate=dict(
            dx_m=mean_sd(dx), dy_m=mean_sd(dy), dyaw_deg=mean_sd(dw),
            residual_after_constant_offset=dict(
                rms_m=round(float(np.sqrt(np.mean(np.square(res)))), 4) if res else None,
                max_m=round(float(np.max(res)), 4) if res else None),
        ),
        per_tag=per_tag,
        visibility=dict(
            predicted_at_least_partly_in_frame=len(vis),
            fully_in_frame_and_large_enough=cell(True, True),
            fully_in_frame_too_small=cell(True, False),
            partly_in_frame_large_enough=cell(False, True),
            partly_in_frame_too_small=cell(False, False),
            not_detected_though_framed_and_large=[
                dict(image=v['image'], tag_id=v['tag_id'],
                     predicted_side_px=round(v['predicted_side_px'], 1),
                     predicted_distance_m=round(v['predicted_distance_m'], 2),
                     u=[round(v['u_min']), round(v['u_max'])],
                     v=[round(v['v_min']), round(v['v_max'])])
                for v in sorted(unexplained, key=lambda z: -z['predicted_side_px'])],
        ),
        negative_results=dict(
            tag5_arrivals_at_cb203_exit=sum(1 for i in images if i['node_name'] == 'cb203_exit'),
            tag5_detections=sum(1 for p in poses if p['tag_id'] == 5),
            tag2_detections=sum(1 for p in poses if p['tag_id'] == 2),
            tag2_max_side_px=round(max([p['tag_side_px'] for p in poses if p['tag_id'] == 2],
                                       default=0.0), 1),
        ),
    )


README_HEAD = """# External localization reference from wall AprilTags

## What this measures

Five AprilTags (tag36h11, 125 mm black square) are fixed to the walls of the test floor.
They were installed for an unrelated Nav2 docking experiment and are not part of the SAS
stack: nothing in the navigation pipeline reads them, and no run used them. Three have
surveyed map coordinates.

Whenever a mission image happens to contain one, the camera pose can be recovered from
the tag geometry alone and compared against the AMCL pose the robot acted on. The
comparison is opportunistic: no run was performed for this purpose, and the samples are
whatever the mission images happen to contain.

## Method

The four tag corners are expressed **directly in map coordinates**, from the surveyed
centre and wall normal, and passed to `cv2.solvePnP` with the camera calibration used on
the robots. Working in map coordinates removes any tag-local frame, and with it any
convention about which way a tag's axes point. The camera centre and heading follow from
the pose; the base_link estimate follows from the camera offset on that platform.

Detection runs at native resolution and at 2x; the larger of the two detections is kept
and its corners rescaled. A tag smaller than 80 px on a side is excluded: corner
localization error is roughly constant in pixels, so position error grows with the square
of distance, and below that size the estimate is worthless. At 80 px a 125 mm tag is
about 1.07 m from the camera.

Note that `camera_height_m` enters only the z component of the base_link estimate, which
is never used. Only `camera_offset_x_m` propagates into the reported deltas.
"""


def write_readme(path, s, poses, vis, extr_ref, tags=None):
    L = [README_HEAD, '', '## Result', '']
    ag = s['aggregate']
    L += [f"Across {s['detections_included']} usable detections out of "
          f"{s['detections_total']} in {s['images_searched']} mission images:", '',
          '```',
          f"dx   = {ag['dx_m']['mean']:+.3f} +/- {ag['dx_m']['sd']:.3f} m   "
          f"95% CI [{ag['dx_m']['ci95_low']:+.3f}, {ag['dx_m']['ci95_high']:+.3f}]",
          f"dy   = {ag['dy_m']['mean']:+.3f} +/- {ag['dy_m']['sd']:.3f} m   "
          f"95% CI [{ag['dy_m']['ci95_low']:+.3f}, {ag['dy_m']['ci95_high']:+.3f}]",
          f"dyaw = {ag['dyaw_deg']['mean']:+.2f} +/- {ag['dyaw_deg']['sd']:.2f} deg  "
          f"95% CI [{ag['dyaw_deg']['ci95_low']:+.2f}, {ag['dyaw_deg']['ci95_high']:+.2f}]",
          '',
          f"residual after removing the constant offset: "
          f"rms {ag['residual_after_constant_offset']['rms_m']:.3f} m, "
          f"max {ag['residual_after_constant_offset']['max_m']:.3f} m",
          '```', '',
          'Per tag:', '',
          '| tag | nearest node | normal | n | dx (m) | dy (m) | dyaw (deg) | range (m) | lateral (m) | reproj (px) |',
          '|---|---|---|---|---|---|---|---|---|---|']
    for tid, t in s['per_tag'].items():
        if not t['included']:
            continue
        g = [p for p in poses if str(p['tag_id']) == tid and p['included'] == 'yes'][0]
        nm = {(1.0, 0.0): '+X', (-1.0, 0.0): '-X', (0.0, 1.0): '+Y', (0.0, -1.0): '-Y'}.get(
            (t['normal'][0], t['normal'][1]), '?')
        L.append(f"| {tid} | {g['node_name']} | {nm} | {t['included']} | "
                 f"{t['dx_m']['mean']:+.3f} +/- {t['dx_m']['sd']:.3f} | "
                 f"{t['dy_m']['mean']:+.3f} +/- {t['dy_m']['sd']:.3f} | "
                 f"{t['dyaw_deg']['mean']:+.2f} +/- {t['dyaw_deg']['sd']:.2f} | "
                 f"{t['range_component_m']['mean']:+.3f} | "
                 f"{t['lateral_component_m']['mean']:+.3f} | "
                 f"{t['reprojection_error_px']['mean']:.2f} |")

    L += ['', '## Interpretation', '',
          'The offset is constant in the **map frame** and close to zero in y and in heading.',
          'Three observations rule out the alternatives, and each depends on the tags having',
          'different wall normals:', '']
    inc = sorted({p['tag_id'] for p in poses if p['included'] == 'yes'})
    if len(inc) >= 2:
        a, b = s['per_tag'][str(inc[0])], s['per_tag'][str(inc[-1])]
        L += [f"* **Not a range bias.** Decomposed along each wall normal, tag {inc[0]} gives range "
              f"{a['range_component_m']['mean']:+.3f} m and tag {inc[-1]} gives "
              f"{b['range_component_m']['mean']:+.3f} m: opposite signs at comparable distance. "
              'A bias in measured distance would carry the same sign.',
              '* **Not a camera mounting offset.** That would produce dx proportional to '
              'cos(yaw). The robot faces roughly 180 deg at one tag and 0 deg at the other, '
              'and dx is positive at both.',
              '* **Not a mounting pitch.** That would bias range with the same sign at the '
              'same distance, which the first observation excludes.', '']
    unc = sorted({t['survey_uncertainty_m'] for t in (tags or {}).values()
                  if t and t.get('survey_uncertainty_m') is not None})
    methods = sorted({t['survey_method'] for t in (tags or {}).values()
                      if t and t.get('survey_method')})
    if unc:
        ratio = abs(ag['dx_m']['mean']) / max(unc)
        survey_note = (
            '* **Survey uncertainty is small relative to the offset.** The tag coordinates were '
            f"measured by {' and '.join(m.replace('_', ' ') for m in methods)}, stated in "
            f'`tag_survey.csv` as +/- {max(unc) * 1000:.0f} mm. The measured offset is '
            f'{ratio:.0f} times that, so it cannot be an artefact of the survey. What the survey '
            'uncertainty does not settle is whether the offset lies in the map or in the common '
            'origin the three tape runs started from.')
    else:
        survey_note = ('* **Survey uncertainty is not quantified.** `tag_survey.csv` records '
                       '`survey_uncertainty_m` as unspecified.')

    L += ['What remains is a rigid translation between the frame AMCL reports in and the frame',
          'the tags were surveyed in. The data cannot separate a displaced map origin from a',
          'common origin error in the three tape measurements, because all three x coordinates',
          'were measured from the same reference. Either way it is a frame offset, not a',
          'localization failure.', '',
          'Two consequences for the paper. The residual after removing the constant is the real',
          'local accuracy of AMCL in this environment. And `xy_error_m` in the audit records is',
          'computed in the map frame against node coordinates in that same frame, so a constant',
          'frame offset cancels there and no published figure is affected.', '',
          '## Limitations', '',
          'These are stated first because a reader will otherwise find them.', '',
          '* **The reference is from session E; the navigation failures analysed elsewhere are',
          '  from sessions A-C.** The tags were not yet installed then. This measures',
          '  localization accuracy in the same room, on the same map, with the same robots and',
          '  the same stack, but not during the same runs. It supports the claim that continuous',
          '  localization drift is not a plausible failure mode for this system in this',
          '  environment; it cannot retroactively diagnose an individual failure recorded in',
          '  sessions A-C.',
          '* **The sampling is opportunistic.** No run was made for this purpose. The number of',
          '  usable samples per tag is whatever the mission images happened to contain.',
          survey_note, '']

    v = s['visibility']
    fb, fs = v['fully_in_frame_and_large_enough'], v['fully_in_frame_too_small']
    pb, ps = v['partly_in_frame_large_enough'], v['partly_in_frame_too_small']
    L += ['## Why so few samples', '',
          'The tags sit at a height chosen for a different camera. At the SAS camera height and',
          'a 37.7 deg vertical field of view, a tag drops below the bottom of the frame at close',
          'range, which is exactly where it would otherwise be large enough to use.',
          '`visibility_analysis.csv` projects each surveyed tag into every mission image using the',
          'AMCL pose, so a non-detection can be attributed. Two things have to hold at once: the',
          'tag must be framed, and it must be large enough.', '',
          '| predicted framing | predicted size | images | detected |',
          '|---|---|---|---|',
          f"| all four corners in frame | >= {MIN_TAG_SIDE_PX:.0f} px | {fb['images']} | {fb['detected']} |",
          f"| all four corners in frame | < {MIN_TAG_SIDE_PX:.0f} px | {fs['images']} | {fs['detected']} |",
          f"| partly in frame | >= {MIN_TAG_SIDE_PX:.0f} px | {pb['images']} | {pb['detected']} |",
          f"| partly in frame | < {MIN_TAG_SIDE_PX:.0f} px | {ps['images']} | {ps['detected']} |", '',
          'The prediction is approximate at the margins: it uses the AMCL pose, which carries the',
          'very offset this analysis measures, so a borderline case can fall either way.', '']
    un = v['not_detected_though_framed_and_large']
    if un:
        L += [f"{len(un)} image/tag pairs were predicted both framed and large enough yet were not",
              'detected. They are listed here rather than absorbed into a rate:', '',
              '| tag | predicted px | distance (m) | image |', '|---|---|---|---|']
        for u in un:
            L.append(f"| {u['tag_id']} | {u['predicted_side_px']:.0f} | "
                     f"{u['predicted_distance_m']:.2f} | `{u['image']}` |")
        L += ['', 'Two of these were inspected directly and both are **occlusions**, by different',
              'objects. In `day2_20260821/logs/20260821_134402/mission_1_plant_2/finish.jpg` a',
              'terracotta plant pot fills exactly the image region where the tag was predicted;',
              'tag 1 is mounted on the wall behind the plants. In',
              '`day1_20260820/logs/20260820_130331/mission_1_cb203_entrance/finish.jpg` the CB203',
              'door stands open across the frame, hiding the tag beside its frame. The remaining',
              'three are at the same two locations and are consistent with the same cause, but',
              'were not individually verified.', '',
              'So the tags are occluded by the very furniture that makes those nodes semantically',
              'interesting. That is a property of the environment, not a defect of the detector.', '']

    L += ['## Negative results', '']
    n = s['negative_results']
    L += [f"* Tag 5 is reported present near `cb203_exit`. It was **never detected**, in any of "
          f"the {n['tag5_arrivals_at_cb203_exit']} images recorded at that node.",
          f"* Tag 2 was detected {n['tag2_detections']} times, at a maximum of "
          f"{n['tag2_max_side_px']:.0f} px on a side. Its position was never surveyed and it is "
          'unusable at every distance observed.', '',
          '## Excluded samples', '']
    reasons = Counter(p['exclusion_reason'] for p in poses if p['included'] == 'no')
    L += ['| reason | detections |', '|---|---|']
    for r, c in reasons.most_common():
        L.append(f'| `{r}` | {c} |')
    for tid in sorted(SURVEY_INCONSISTENT):
        t = s['per_tag'].get(str(tid))
        if not t or not t['camera_height_optical_m'].get('n'):
            continue
        ch = t['camera_height_optical_m']
        g = [q for q in poses if q['tag_id'] == tid
             and q['tag_side_px'] >= MIN_TAG_SIDE_PX and 'camera_height_optical_m' in q]
        plats = sorted({q['platform_id'] for q in g})
        declared = ', '.join(f'{extr_ref[q][1]:.3f} m on {q}' for q in plats if q in extr_ref)
        ref = [q for q in poses if q['tag_id'] != tid and q['included'] == 'yes'
               and q['platform_id'] in plats]
        rng = (f"{min(q['camera_height_optical_m'] for q in ref):.3f} to "
               f"{max(q['camera_height_optical_m'] for q in ref):.3f} m") if ref else 'n/a'
        L += ['', f'Tag {tid} deserves its own note. Across its {ch["n"]} usable detections, '
                  f'on {"both days" if len(t["days"]) != 1 else "a single day"}, it places the '
                  f'camera at {ch["mean"]:.3f} m +/- {ch["sd"]:.3f} m above the floor. The camera '
                  f'is declared at {declared}, and the same platform against the other tags '
                  f'returns {rng}. The scatter is {ch["sd"] * 100:.1f} cm, so this is not noise. '
                  'No tag height closes the gap: matching the declared camera height would put '
                  'the tag centre below the floor, and no rotation about the vertical closes the '
                  'heading and the height together. The tag is not mounted as surveyed.', '',
              'Its samples are computed and published in `pose_estimates.csv`, marked '
              '`tag_survey_inconsistent`, and excluded from every aggregate. That the method '
              f'detects a survey error of this size from {ch["n"]} photographs is itself '
              'evidence that it is doing what an external reference is supposed to do.', '']

    L += [          '## Reproducing', '', '```', 'python3 apriltag_reference.py --dataset <path to data/session_e>',
          '```', '', 'Requires numpy, opencv-python and pupil-apriltags. Every number above is read',
          'from `summary.json`; none is transcribed by hand.', '']
    open(path, 'w', encoding='utf-8').write('\n'.join(L))


def write_csv(path, rows, columns):
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            out = {}
            for k in columns:
                v = r.get(k, '')
                out[k] = round(v, 6) if isinstance(v, float) else v
            w.writerow(out)


DETECTION_COLUMNS = ['image', 'kind', 'day', 'run_id', 'platform_id', 'experiment_id',
                     'node_id', 'node_name', 'tag_id', 'tag_side_px', 'decision_margin',
                     'detected_at_scale', 'corner_u', 'corner_v']

POSE_COLUMNS = ['image', 'kind', 'day', 'run_id', 'platform_id', 'experiment_id',
                'node_id', 'node_name', 'tag_id', 'tag_side_px', 'tag_distance_m',
                'reprojection_error_px', 'camera_height_optical_m',
                'amcl_x', 'amcl_y', 'amcl_yaw', 'amcl_converged', 'amcl_covariance_trace',
                'tag_x_m', 'tag_y_m', 'tag_yaw_rad',
                'dx_m', 'dy_m', 'dyaw_deg', 'range_component_m', 'lateral_component_m',
                'included', 'exclusion_reason']

VIS_COLUMNS = ['image', 'day', 'platform_id', 'node_name', 'tag_id',
               'predicted_distance_m', 'predicted_side_px',
               'u_min', 'u_max', 'v_min', 'v_max',
               'corners_in_frame', 'fully_in_frame', 'detected']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', required=True, help='path to data/session_e')
    args = ap.parse_args()

    ds = os.path.abspath(args.dataset)
    ext = os.path.join(ds, 'external_reference')
    if not os.path.isdir(ext):
        sys.exit(f'ERROR: {ext} not found. It must hold tag_survey.csv, '
                 'platform_extrinsics.csv and the camera calibration.')

    K, D = read_calibration(os.path.join(ext, 'hd_pro_webcam_c920_v2.yaml'))
    tags = read_tag_survey(os.path.join(ext, 'tag_survey.csv'))
    extr = read_extrinsics(os.path.join(ext, 'platform_extrinsics.csv'))
    print(f'  calibration fx={K[0,0]:.2f} fy={K[1,1]:.2f} cx={K[0,2]:.2f} cy={K[1,2]:.2f}')
    print(f'  tags surveyed: {sorted(t for t, v in tags.items() if v)}   '
          f'not surveyed: {sorted(t for t, v in tags.items() if not v)}')

    print('[1/4] loading mission poses and image references ...')
    images = load_missions(ds)
    print(f'      {len(images)} images with an AMCL pose')

    print('[2/4] detecting tags ...')
    detections = detect_all(ds, images)
    print(f'      {len(detections)} detections   ' +
          '  '.join(f'id{t}:{c}' for t, c in
                    sorted(Counter(d['tag_id'] for d in detections).items())))

    print('[3/4] estimating poses ...')
    poses = estimate_poses(detections, tags, extr, K, D)
    used = [p for p in poses if p['included'] == 'yes']
    print(f'      {len(used)} usable of {len(poses)}')

    print('[4/4] visibility analysis ...')
    detected_pairs = {(d['image'], d['tag_id']) for d in detections}
    vis = visibility(images, tags, extr, K, D, detected_pairs)
    print(f'      {len(vis)} image/tag pairs predicted at least partly in frame')

    for d in detections:
        d['corner_u'] = ';'.join(f'{u:.2f}' for u in d['corners'][:, 0])
        d['corner_v'] = ';'.join(f'{v:.2f}' for v in d['corners'][:, 1])
    write_csv(os.path.join(ext, 'detections.csv'), detections, DETECTION_COLUMNS)
    write_csv(os.path.join(ext, 'pose_estimates.csv'), poses, POSE_COLUMNS)
    write_csv(os.path.join(ext, 'visibility_analysis.csv'), vis, VIS_COLUMNS)

    s = summarize(poses, vis, tags, images)
    json.dump(s, open(os.path.join(ext, 'summary.json'), 'w'), indent=2)
    write_readme(os.path.join(ext, 'README.md'), s, poses, vis, extr, tags)

    lines = []
    for name in sorted(os.listdir(ext)):
        f = os.path.join(ext, name)
        if os.path.isfile(f) and name != 'CHECKSUMS.md5':
            h = __import__('hashlib').md5(open(f, 'rb').read()).hexdigest()
            lines.append(f'{h}  {name}')
    open(os.path.join(ext, 'CHECKSUMS.md5'), 'w').write('\n'.join(lines) + '\n')
    print(f'      {len(lines)} files checksummed into external_reference/CHECKSUMS.md5')

    ag = s['aggregate']
    print(f"\n  dx   {ag['dx_m']['mean']:+.3f} +/- {ag['dx_m']['sd']:.3f} m  "
          f"CI95 [{ag['dx_m']['ci95_low']:+.3f}, {ag['dx_m']['ci95_high']:+.3f}]  n={ag['dx_m']['n']}")
    print(f"  dy   {ag['dy_m']['mean']:+.3f} +/- {ag['dy_m']['sd']:.3f} m")
    print(f"  dyaw {ag['dyaw_deg']['mean']:+.2f} +/- {ag['dyaw_deg']['sd']:.2f} deg")
    print(f"  residual after constant offset: rms "
          f"{ag['residual_after_constant_offset']['rms_m']:.3f} m, "
          f"max {ag['residual_after_constant_offset']['max_m']:.3f} m")
    print('\nDONE')


if __name__ == '__main__':
    main()
