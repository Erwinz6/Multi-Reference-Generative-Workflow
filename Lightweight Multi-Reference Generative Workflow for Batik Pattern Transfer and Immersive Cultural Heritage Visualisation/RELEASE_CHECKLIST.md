# Release Checklist

Use this checklist before pushing a public release.

## Code and Config

- remove machine-specific secrets and private paths if possible,
- confirm ports and path assumptions are documented,
- confirm core scripts still run after refactoring,
- confirm the public UE listener is the simplified template version.

## Assets and Data

- do not include private Unreal Engine project content,
- do not include copyrighted scene assets,
- do not include model weights unless redistribution is permitted,
- do not include experiment logs, generated CSV outputs, or large local datasets.

## Documentation

- update `README.md`,
- update `NOTICE.md`,
- update `docs/setup/ue_setup.md`,
- verify reproduction instructions are still correct.

## Final Check

- review `.gitignore`,
- check repository size,
- verify license compatibility,
- run one minimal end-to-end test with public-safe settings.
