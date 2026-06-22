# Release consensus artifacts

AgentMesh (private repository) exports one JSON file per stable release. Commit the file here before tagging `main`.

## Generate (private AgentMesh clone)

```bash
agentmesh release verify \
  --project veripatch \
  --version 1.1.0 \
  --output /path/to/veripatch/release/consensus/v1.1.0.json
```

## Validate (this repo)

```bash
python scripts/validate-release-consensus.py --version 1.1.0
```

CI runs the same validation on every stable tag before building the Windows installer.
