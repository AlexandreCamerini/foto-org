# Coding Conventions

**Analysis Date:** 2026-08-16

This is a bilingual-by-design codebase: **all identifiers, docstrings, comments,
error messages and commit messages are in Portuguese (PT-BR)**. Do not introduce
English names into `fotoorganizer/` or `webapp/src/` — mixed-language code is an
immediate readability regression here. Prose comments are long-form and
explain *why*, often citing a concrete number from the user's real catalog
(e.g. "89% do acervo local eram miniaturas 540×360") or a decision ID from
`docs/DECISOES.md` (e.g. "D-024", "D-068"). Follow this style: a one-line
comment stating a rule is less valuable here than a short paragraph stating
the rule plus the incident that produced it.

No linter or formatter is configured for either side of the codebase (no
`ruff`, `flake8`, `black`, `.eslintrc`, `.prettierrc`). Style consistency is
maintained by convention and code review (see `.claude/skills/fatia-vertical/SKILL.md`
step 7: a fresh-eyes subagent reviews every diff before commit), not by
tooling. Match the surrounding file's style exactly; there is no autoformatter
to fall back on.

## Naming Patterns

**Files (Python):**
- `snake_case.py`, one module per concern, grouped by domain package
  (`fotoorganizer/grouping/classifier.py`, `fotoorganizer/security/http_seguro.py`).
- Test files mirror the module under test: `tests/test_<modulo>.py`
  (`fotoorganizer/scanner/discovery.py` → `tests/test_discovery.py`).

**Files (TypeScript/React):**
- `PascalCase.tsx` for components (`webapp/src/components/Duplicates.tsx`).
- `camelCase.ts`/`.tsx` for hooks, prefixed `use` (`webapp/src/hooks/useJob.ts`).
- Colocated test: `Component.test.tsx` next to `Component.tsx`.

**Functions and variables:**
- Portuguese, `snake_case` in Python: `agrupar_viagens`, `resolver_destino`,
  `caminho_relativo_seguro`. Booleans read as a yes/no question in context,
  not prefixed with `is_`/`has_` (`organizavel`, `disponivel`).
- Private/internal helpers prefixed `_` (`_dias`, `_chave`, `_TIPO_EFETIVO`,
  `_ACERVO`). Module-level constants are `_UPPER_SNAKE` when private
  (`_MAX_SEGMENTO`, `_TIMEOUT_S`) or `UPPER_SNAKE` when part of the public
  contract (`ORDENACOES`, `ALCANCES`, `LACUNAS` in `fotoorganizer/repositories/media.py`).
- TypeScript: `camelCase` functions/variables in Portuguese (`servirApi`,
  `montar`, `jobParado`, `reconectar`), `PascalCase` for types/interfaces
  (`JobEstado`, `Chamada`).

**Types/Classes:**
- Python classes `PascalCase`: ORM models (`MediaFile`, `Source`,
  `ScanSession`), dataclasses (`ClusterInfo`, `AdvisorResult`), custom
  exceptions (`CaminhoInvalido`, `ErroDeDownload`, `TamanhoExcedido`).
- Enums use `enum.StrEnum` with Portuguese string values, defined next to the
  model that uses them (`fotoorganizer/models/catalog.py`): `ScanStatus`,
  `SourceType`, `MediaRole`, `ReviewStatus`. Each nontrivial enum member gets
  a comment or the whole enum gets a docstring explaining the domain
  distinction (see `MediaRole` — ACERVO vs SINAL, tied to invariant 8 in
  `CLAUDE.md`).

## Code Style

**Formatting:** No formatter configured. Match existing indentation (4
spaces Python, 2 spaces TS), line-wrap around ~88-100 cols, trailing commas
in multi-line Python calls/collections.

**Linting:** None configured (no ruff/flake8/eslint). TypeScript strictness
is enforced entirely through `tsconfig.app.json`: `strict: true`,
`noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`. `npm
run build` (`tsc -b && vite build`) is the de facto lint gate — it must pass
as part of `scripts/verificar.sh`.

**Python version idioms:** Python 3.12+ throughout. `from __future__ import
annotations` at the top of nearly every module (83+ occurrences) to allow
`X | None` unions and forward references without runtime cost.
`enum.StrEnum` used for all string enums (available since 3.11).
`@dataclass(frozen=True, slots=True)` for immutable value objects
(`fotoorganizer/classification/advisor.py`).

## Import Organization

**Order (Python):** standard library, then third-party, then
`fotoorganizer.*` — matches `isort`/PEP 8 defaults even though no tool
enforces it. Example (`fotoorganizer/repositories/media.py`):
```python
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, aliased, sessionmaker

from fotoorganizer.metadata.base import NAMESPACE_CURADORIA
from fotoorganizer.metadata.camera import nome_da_camera
from fotoorganizer.models import (...)
```

**Order (TypeScript):** third-party libraries, then relative imports, blank
line between groups. Type-only imports use `import type`:
```typescript
import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import Duplicates from "./Duplicates";
import type { Job } from "../hooks/useJob";
import { montar, servirApi } from "../test/servidor";
```

**Path aliases:** None configured on either side — imports are always
relative (`./Component`) or fully-qualified (`fotoorganizer.module.submodule`).

## Error Handling

**Python — domain-specific exception hierarchies:** every module that can
fail defines its own exception classes rather than raising bare
`ValueError`/`OSError`. Base class inherits from a stdlib exception or a
narrow local base; specific failures subclass it so callers can catch broad
or narrow as needed. Example from `fotoorganizer/security/http_seguro.py`:
`ErroDeDownload` is the umbrella (documented contract: "tudo que sai de
`baixar_arquivo` é `ErroDeDownload`"), with `UrlInvalida`, `EsquemaNaoPermitido`,
`TamanhoExcedido`, `CorpoNaoConfere`, `ErroHTTP`, `ErroDeRede`, `TempoEsgotado`,
`DestinoJaExiste`, `ErroDeArquivo` as concrete subclasses. Exceptions carry
structured data as attributes for assertions (`TamanhoExcedido.limite`,
`CorpoNaoConfere.declarado`/`.lidos`), not just a message string.

**Wrapping foreign exceptions:** low-level errors (`OSError`, `PermissionError`)
are caught at the boundary and re-raised as the module's own exception type
with `raise ... from exc` so `__cause__` is preserved and inspectable in
tests (`fotoorganizer/security/http_seguro.py`, see
`test_link_nao_suportado_vira_erro_do_modulo` in
`tests/test_http_seguro.py`). Never let a raw stdlib exception escape a
module's public contract.

**FastAPI layer (`fotoorganizer/server/app.py`):** catch domain exceptions
per-route and translate to `HTTPException` with the right HTTP status —
`404` for missing entity, `409` for a state conflict (job already running,
operation not applicable), `422` for invalid input/`ValueError`. Message is
always the exception's string form or a short Portuguese phrase:
```python
except ReapontamentoInaplicavel as exc:
    raise HTTPException(409, str(exc))
...
raise HTTPException(422, f"lacuna desconhecida: {lacuna}")
```

**Read/scan failures never abort the batch.** Per `CLAUDE.md`: "Erros de
leitura de arquivo nunca derrubam a varredura: registrar e continuar." Scanner
and metadata-extraction code must log-and-continue on a single-file failure,
not propagate and stop the whole run.

**Frontend error simulation:** the test double `webapp/src/test/servidor.tsx`
provides an explicit `erro(status, detail)` helper so component tests can
exercise non-happy-path API responses (409/422) rather than only mocking
success. Unrouted paths return 404 with a message naming the missing route,
so a broken fixture fails loudly instead of surfacing `undefined`.

## Logging

**Framework:** Not directly inspected beyond `fotoorganizer/config` and
`tests/test_logsetup.py`; project rule from `CLAUDE.md`: "logging estruturado
sem conteúdo sensível" — never log photo paths' full contents, EXIF payload,
or any personal data beyond what's needed to diagnose.

## Comments

**When to comment:** liberally, and always to explain *why*, frequently
anchored to a concrete incident or measurement from the real catalog, not
just *what* the code does. This is the dominant style across the codebase —
see `fotoorganizer/repositories/media.py`'s `_acervo_ao_alcance` docstring
(cites "2.405 fotos" and "D-068") or `MediaRole`'s docstring (cites "89%",
"540×360", "D-024"). When adding a non-obvious rule, cite the number or
decision that justifies it if one exists in `docs/DECISOES.md`.

**Docstrings:** Python modules and public functions get a one-to-few-line
docstring stating purpose and any non-obvious contract/invariant. Test
functions often carry a docstring instead of a comment, explaining the
real-world scenario the test protects against (see `test_grouping.py`'s
`test_pasta_que_lista_destinos_nomeia_a_viagem_inteira`).

**TSDoc:** Multi-line `/** ... */` comments on hooks/exported helpers
explaining behavior and edge cases (`webapp/src/hooks/useJob.ts`,
`webapp/src/test/servidor.tsx`).

## Function Design

**Size:** Small, single-purpose functions; complex flows are split into
named private helpers (`_acervo_ao_alcance`, `_condicao_lacuna`, `_promover`,
`_dias`) rather than inlined. Query-building functions in repositories
compose SQLAlchemy expressions from smaller named predicates rather than one
large query literal.

**Parameters:** Keyword-only for optional/tunable parameters in public APIs,
e.g. `baixar_arquivo(url, destino, *, tamanho_maximo_bytes=..., timeout=...,
sobrescrever=False)`. Defaults are conservative/safe (`sobrescrever=False`
matches the project's non-destructive invariant).

**Return values:** Prefer raising a typed exception over returning
sentinel/`None` for failure. Functions that need to report enriched failure
context put it on the exception instance, not the return value.

## Module Design

**Exports:** No barrel files (`__init__.py` used for package markers and, in
`fotoorganizer/models/__init__.py`, to re-export the ORM model surface for
convenient `from fotoorganizer.models import (...)` imports elsewhere).

**Protocol-based extension points:** swappable infrastructure is defined as
a `typing.Protocol` plus a null/stub implementation and one or more real
implementations, matching `CLAUDE.md`'s "Componentes substituíveis
(Protocol)" list (`MetadataExtractor`, `VisionProvider`,
`FaceRecognitionProvider`, `GeocodingProvider`, `SyncProvider`). Example
pattern (`fotoorganizer/classification/advisor.py`):
```python
class ClassificationAdvisor(Protocol):
    def local(self) -> bool: ...
    def classificar(self, cluster: ClusterInfo) -> AdvisorResult | None: ...

class NullAdvisor:
    def local(self) -> bool: ...
    def classificar(self, cluster: ClusterInfo) -> AdvisorResult | None: ...

class ClaudeAdvisor:
    def __init__(self, model: str = MODELO_PADRAO, client=None) -> None: ...
```
When adding a new pluggable capability, follow this three-part shape: define
the `Protocol`, provide a `Null*`/stub default (safe, offline, no-op), then
the real implementation behind an explicit opt-in.

**React components:** function components, hooks for cross-cutting state
(`useJob`), presentational components accept typed props including the
relevant hook's return type (`job: Job`). Component tests build fixtures
with small factory functions (`membro(over)`, `grupo(over)`) that take an
overrides object rather than a full literal per test.

---

*Convention analysis: 2026-08-16*
