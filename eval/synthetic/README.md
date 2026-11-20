# Synthetic imperfect packet

`Rivera,_Jordan_AU99999_OPHTH-R_SYNTHETIC.pdf` is a **fictional** ophthalmology residency packet built to exercise green, yellow, and red in the circle UI.

Regenerate:

```bash
python eval/synthetic/make_imperfect_packet.py
```

Designed colors (when the filename contains `_SYNTHETIC` or `AU99999`):

| Reader | Color | Why |
| --- | --- | --- |
| Statement | Green | Concrete cataract story |
| Letters | Yellow | Empty praise, no clinical examples |
| Research | Red | Titles only, no applicant role |
| Clinical | Green | Specific MSPE praise |
| Academics | Yellow | Thin education / Step 1 Pass only |
| Commitment | Red | Half-day shadowing only outside the statement |

Evidence quotes still come from the packet text. This is a UI calibration fixture, not a live model judgment of a real applicant.
