# launch/

All marketing, launch, and go-to-market work for the POT Matchmaker lives here.

Pre-launch briefs go in first. Once a campaign ships, the final assets, post-mortem, and metrics get filed alongside the brief so the next campaign has full context.

## Structure

```
launch/
├── README.md                              this file
├── 2026-05-launch-video-brief.md          hero video creative brief (current)
├── assets/                                final exported video files, posters, audio (created on production)
│   └── ...
└── post-mortems/                          campaign retros + metrics after each launch
    └── ...
```

## Conventions

- File names use the date the asset was conceived, not shipped: `YYYY-MM-<slug>.md`.
- Briefs are immutable once approved. Changes go in a new `-revB.md` file with a top-line note pointing back to the original.
- Drop raw video / image exports in `assets/` and link from the brief. Don't commit files > 25 MB to git — store on Google Drive and link.
- Post-launch: write a one-page post-mortem in `post-mortems/` covering reach, CTR, replies, ticket conversions, and one lesson for next time.

## Adjacent docs

- Product positioning + audience size: `docs/architecture-scale.md`
- Live attendee count + funnel: backend dashboard `/dashboard`
- Email infrastructure (sender, templates, status): `backend/app/services/email.py`
