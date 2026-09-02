# External localization reference from wall AprilTags

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


## Result

Across 11 usable detections out of 29 in 345 mission images:

```
dx   = +0.208 +/- 0.042 m   95% CI [+0.183, +0.233]
dy   = +0.030 +/- 0.060 m   95% CI [-0.006, +0.065]
dyaw = -2.30 +/- 4.26 deg  95% CI [-4.82, +0.21]

residual after removing the constant offset: rms 0.070 m, max 0.104 m
```

Per tag:

| tag | nearest node | normal | n | dx (m) | dy (m) | dyaw (deg) | range (m) | lateral (m) | reproj (px) |
|---|---|---|---|---|---|---|---|---|---|
| 3 | toilet_m | +X | 10 | +0.205 +/- 0.044 | +0.020 +/- 0.054 | -2.42 +/- 4.47 | +0.205 | +0.020 | 0.58 |
| 4 | cb203_entrance | -X | 1 | +0.233 +/- 0.000 | +0.127 +/- 0.000 | -1.15 +/- 0.00 | -0.233 | -0.127 | 0.23 |

## Interpretation

The offset is constant in the **map frame** and close to zero in y and in heading.
Three observations rule out the alternatives, and each depends on the tags having
different wall normals:

* **Not a range bias.** Decomposed along each wall normal, tag 3 gives range +0.205 m and tag 4 gives -0.233 m: opposite signs at comparable distance. A bias in measured distance would carry the same sign.
* **Not a camera mounting offset.** That would produce dx proportional to cos(yaw). The robot faces roughly 180 deg at one tag and 0 deg at the other, and dx is positive at both.
* **Not a mounting pitch.** That would bias range with the same sign at the same distance, which the first observation excludes.

What remains is a rigid translation between the frame AMCL reports in and the frame
the tags were surveyed in. The data cannot separate a displaced map origin from a
common origin error in the three tape measurements, because all three x coordinates
were measured from the same reference. Either way it is a frame offset, not a
localization failure.

Two consequences for the paper. The residual after removing the constant is the real
local accuracy of AMCL in this environment. And `xy_error_m` in the audit records is
computed in the map frame against node coordinates in that same frame, so a constant
frame offset cancels there and no published figure is affected.

## Limitations

These are stated first because a reader will otherwise find them.

* **The reference is from session E; the navigation failures analysed elsewhere are
  from sessions A-C.** The tags were not yet installed then. This measures
  localization accuracy in the same room, on the same map, with the same robots and
  the same stack, but not during the same runs. It supports the claim that continuous
  localization drift is not a plausible failure mode for this system in this
  environment; it cannot retroactively diagnose an individual failure recorded in
  sessions A-C.
* **The sampling is opportunistic.** No run was made for this purpose. The number of
  usable samples per tag is whatever the mission images happened to contain.
* **Survey uncertainty is small relative to the offset.** The tag coordinates were measured by tape measure, stated in `tag_survey.csv` as +/- 5 mm. The measured offset is 42 times that, so it cannot be an artefact of the survey. What the survey uncertainty does not settle is whether the offset lies in the map or in the common origin the three tape runs started from.

## Why so few samples

The tags sit at a height chosen for a different camera. At the SAS camera height and
a 37.7 deg vertical field of view, a tag drops below the bottom of the frame at close
range, which is exactly where it would otherwise be large enough to use.
`visibility_analysis.csv` projects each surveyed tag into every mission image using the
AMCL pose, so a non-detection can be attributed. Two things have to hold at once: the
tag must be framed, and it must be large enough.

| predicted framing | predicted size | images | detected |
|---|---|---|---|
| all four corners in frame | >= 80 px | 15 | 10 |
| all four corners in frame | < 80 px | 51 | 10 |
| partly in frame | >= 80 px | 15 | 6 |
| partly in frame | < 80 px | 59 | 0 |

The prediction is approximate at the margins: it uses the AMCL pose, which carries the
very offset this analysis measures, so a borderline case can fall either way.

5 image/tag pairs were predicted both framed and large enough yet were not
detected. They are listed here rather than absorbed into a rate:

| tag | predicted px | distance (m) | image |
|---|---|---|---|
| 1 | 142 | 0.61 | `day2_20260821/logs/20260821_134402/mission_1_plant_2/finish.jpg` |
| 1 | 110 | 0.78 | `day2_20260821/logs/20260821_121718/mission_1_plant_3/finish.jpg` |
| 4 | 103 | 0.83 | `day1_20260820/logs/20260820_130331/mission_1_cb203_entrance/finish.jpg` |
| 1 | 98 | 0.87 | `day2_20260821/logs/20260821_111411/mission_6_plant_3/finish.jpg` |
| 4 | 86 | 1.00 | `day2_20260821/logs/20260821_120446/mission_1_cb203_entrance/finish.jpg` |

Two of these were inspected directly and both are **occlusions**, by different
objects. In `day2_20260821/logs/20260821_134402/mission_1_plant_2/finish.jpg` a
terracotta plant pot fills exactly the image region where the tag was predicted;
tag 1 is mounted on the wall behind the plants. In
`day1_20260820/logs/20260820_130331/mission_1_cb203_entrance/finish.jpg` the CB203
door stands open across the frame, hiding the tag beside its frame. The remaining
three are at the same two locations and are consistent with the same cause, but
were not individually verified.

So the tags are occluded by the very furniture that makes those nodes semantically
interesting. That is a property of the environment, not a defect of the detector.

## Negative results

* Tag 5 is reported present near `cb203_exit`. It was **never detected**, in any of the 16 images recorded at that node.
* Tag 2 was detected 2 times, at a maximum of 19 px on a side. Its position was never surveyed and it is unusable at every distance observed.

## Excluded samples

| reason | detections |
|---|---|
| `tag_side_below_80px` | 12 |
| `tag_survey_inconsistent` | 4 |
| `tag_not_surveyed` | 2 |

Tag 1 deserves its own note. Across its 4 usable detections, on both days, it places the camera at 0.331 m +/- 0.014 m above the floor. The camera is declared at 0.170 m on xplorer-c, and the same platform against the other tags returns 0.048 to 0.171 m. The scatter is 1.4 cm, so this is not noise. No tag height closes the gap: matching the declared camera height would put the tag centre below the floor, and no rotation about the vertical closes the heading and the height together. The tag is not mounted as surveyed.

Its samples are computed and published in `pose_estimates.csv`, marked `tag_survey_inconsistent`, and excluded from every aggregate. That the method detects a survey error of this size from 4 photographs is itself evidence that it is doing what an external reference is supposed to do.

## Reproducing

```
python3 apriltag_reference.py --dataset <path to data/session_e>
```

Requires numpy, opencv-python and pupil-apriltags. Every number above is read
from `summary.json`; none is transcribed by hand.
