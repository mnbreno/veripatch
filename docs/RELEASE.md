# VeriPatch stable releases

Stable releases publish a **Windows installer** on GitHub Releases. Publication requires **AgentMesh agent consensus** and a green CI run on `main`.

## Branch and tag flow

1. Develop on `staging`.
2. Bump version in `backend/pyproject.toml` and update `CHANGELOG.md`.
3. Run AgentMesh release gate (private AgentMesh repository, local clone):

   ```bash
   agentmesh release verify \
     --project veripatch \
     --version 1.1.0 \
     --output release/consensus/v1.1.0.json
   ```

4. Commit the consensus file under `release/consensus/`.
5. Open PR: `staging` → `main`.
6. After merge, tag on `main`:

   ```bash
   git tag v1.1.0
   git push origin v1.1.0
   ```

7. GitHub Actions validates consensus, builds `VeriPatch-{version}-Setup.exe`, and attaches it to the release.

## Agent consensus

The consensus JSON must show:

- `consensus.approved: true`
- `consensus.production_ready: true` (reality-checker)
- Verdicts from `devops-automator`, `code-reviewer`, and `reality-checker`

Use a local LLM for richer review:

```powershell
$env:AGENTMESH_BRAIN = "llm"
$env:AGENTMESH_LLM_BASE_URL = "http://127.0.0.1:1234/v1"
$env:AGENTMESH_LLM_MODEL = "your-model"
agentmesh release verify --version 1.1.0 --output release/consensus/v1.1.0.json
```

## Build installer locally (Windows)

Requires [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`iscc.exe` on PATH).

```powershell
.\scripts\build-windows-installer.ps1
# Optional: bundle wxLua from tools/wxlua542 if present
.\scripts\build-windows-installer.ps1 -WxLuaDir "tools\wxlua542"
```

Output: `artifacts/VeriPatch-{version}-Setup.exe`

## Prerequisites bundled vs required

The installer bundles:

- VeriPatch backend (embedded Python 3.12)
- GUI sources and launcher scripts

**wxLua** is bundled when `-WxLuaDir` is provided at build time; otherwise the launcher searches PATH / `%LOCALAPPDATA%` installs.

## Rollback

Delete the GitHub release and tag if consensus or installer validation fails after publish. Fix on `staging` and repeat the flow.
