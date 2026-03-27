# Grocery.io Session Handoff

This document is a compact restart point for a new Codex session. It focuses on the parts of the codebase that changed recently, the invariants that now matter, and the commands needed to verify behavior without re-reading the whole project.

## Repo Layout

- `android/`
  - Android app, Room DB, Compose UI, gRPC client.
- `db_server/`
  - Python gRPC server, SQLite DB, optimization logic, parser serving path.
- `ai_server/`
  - AI training, labeler, checkpoint generation.
- `protos/db_service.proto`
  - Shared contract between Android and `db_server`.

## Current High-Level Design

- Product/catalog units use `ProductUnit`.
- Grocery-list requested quantity units use `RequestedQuantityUnit`.
- `OZ` means weight only.
- `FL_OZ` is separate for volume.
- `CUP` exists in both product and requested-unit domains.
- Server-side optimization math canonicalizes internally to:
  - mass/weight -> grams
  - volume -> mL
  - count -> item
- Variable-weight items are treated as `pack_count = 1` in the UI/observation flow.

## AI / Checkpoints

- Stable deployment checkpoint alias is now:
  - `ai_server/outputs/local-run/best.pt`
- Training scripts also save archival timestamped checkpoints:
  - `best-<timestamp>.pt`
- Current behavior:
  - `train.py` writes:
    - `best-<timestamp>.pt`
    - `best.pt`
    - `best_custom.pt`
  - `train_hf.py` writes:
    - `best-<timestamp>.pt`
    - `best.pt`
    - `best_hf.pt`
- This matters because the live server is typically pinned to `best.pt` and hot-reloads on file mtime changes.

## Server / Parser Notes

- `db_server/parsing.py`
  - long-lived queued model worker
  - hot reload on checkpoint mtime change
  - supports both custom and legacy HF checkpoint families
  - compile enabled for native/custom path
- Real smoke test with AI is now the default:
  - `./ai_server/.venv/bin/python -m db_server.smoke_test`
- Fake-parser smoke path is opt-out:
  - `./ai_server/.venv/bin/python -m db_server.smoke_test --disable-ai`

## Recent Data Model Changes

### Membership / Loyalty Flags

These now exist end to end.

- Store:
  - `requires paid membership`
- Sale:
  - `requires paid membership`
  - `requires loyalty/membership card`

Rules:

- If store requires paid membership, sale paid-membership and loyalty-card are forced true in the Android UI.
- Existing rows default to `false`.

Relevant files:

- Android:
  - `android/app/src/main/java/com/example/grocerystoreorganizer/data/local/entity/Store.kt`
  - `android/app/src/main/java/com/example/grocerystoreorganizer/data/local/entity/Sale.kt`
  - `android/app/src/main/java/com/example/grocerystoreorganizer/ui/additem/AddItemScreen.kt`
  - `android/app/src/main/java/com/example/grocerystoreorganizer/ui/additem/AddGroceryItemViewModel.kt`
  - `android/app/src/main/java/com/example/grocerystoreorganizer/data/remote/repository/GrpcModelMapper.kt`
  - `android/app/src/main/java/com/example/grocerystoreorganizer/data/local/db/LocalDatabase.kt`
- Server:
  - `protos/db_service.proto`
  - `db_server/domain/commands.py`
  - `db_server/domain/observation.py`
  - `db_server/repositories/grocery.py`
  - `db_server/server.py`
  - `db_server/db/migrations/005_add_membership_flags.sql`

### Store Coordinates Are Now Optional

Store identity is by address. Coordinates are optional metadata.

Implications:

- Manual/offline price observation can save with address only.
- `Use current location` still fills address + coordinates.
- Store rows keep coordinates when available.
- Optimization responses may omit store coordinates.

Relevant files:

- Android:
  - `android/app/src/main/java/com/example/grocerystoreorganizer/data/local/entity/Store.kt`
  - `android/app/src/main/java/com/example/grocerystoreorganizer/data/local/repository/PriceObservationDto.kt`
  - `android/app/src/main/java/com/example/grocerystoreorganizer/data/local/repository/GroceryStoreRepository.kt`
  - `android/app/src/main/java/com/example/grocerystoreorganizer/data/local/repository/StoreLookupRepository.kt`
  - `android/app/src/main/java/com/example/grocerystoreorganizer/data/local/dao/StoreDao.kt`
  - `android/app/src/main/java/com/example/grocerystoreorganizer/data/remote/repository/GrpcModelMapper.kt`
  - `android/app/src/main/java/com/example/grocerystoreorganizer/data/remote/repository/ShoppingOptimizationModels.kt`
  - `android/app/src/main/java/com/example/grocerystoreorganizer/ui/additem/AddItemScreen.kt`
  - `android/app/src/main/java/com/example/grocerystoreorganizer/ui/additem/AddGroceryItemViewModel.kt`
  - `android/app/src/main/java/com/example/grocerystoreorganizer/data/local/db/LocalDatabase.kt`
  - `android/app/src/androidTest/java/com/example/grocerystoreorganizer/data/local/db/LocalDatabaseMigrationTest.kt`
- Server:
  - `db_server/domain/commands.py`
  - `db_server/domain/observation.py`
  - `db_server/repositories/grocery.py`
  - `db_server/server.py`
  - `db_server/db/migrations/006_make_store_coordinates_optional.sql`

## Room DB Versions / Migrations

Current Android Room version:

- `13`

Migration chain currently in use:

- `10 -> 11`
  - desired grocery quantity from integer to real
- `11 -> 12`
  - membership / loyalty flags
- `12 -> 13`
  - store latitude/longitude become nullable

Files:

- `android/app/src/main/java/com/example/grocerystoreorganizer/data/local/db/LocalDatabase.kt`
- `android/app/src/main/java/com/example/grocerystoreorganizer/data/local/db/DatabaseProvider.kt`

## Server DB Migrations

Current notable migrations:

- `005_add_membership_flags.sql`
- `006_make_store_coordinates_optional.sql`

Important:

- restart the DB server after schema changes so the migrations run.

## Optimization / Filtering

Optimization request now supports explicit filtering flags:

- `allowPaidMembershipRequired`
- `allowLoyaltyCardRequired`

Optimization response now includes:

- store-level `requiresPaidMembership`
- match-level `requiresPaidMembership`
- match-level `requiresLoyaltyCard`

Current state:

- server-side filtering is implemented and tested
- Android request/response mapping exists
- there is not yet a user-facing filter UI on the grocery list screen

Key files:

- `protos/db_service.proto`
- `db_server/repositories/grocery.py`
- `db_server/server.py`
- `android/app/src/main/java/com/example/grocerystoreorganizer/data/remote/repository/ShoppingOptimizationModels.kt`
- `android/app/src/main/java/com/example/grocerystoreorganizer/data/remote/repository/GrpcModelMapper.kt`

## No-UPC Behavior

- Real UPCs remain strings.
- Synthetic internal IDs are string-prefixed, not fake numeric UPCs.
- Prefixes:
  - `vw:` for variable-weight no-UPC items
  - `noupc:` for generic no-UPC items

This avoids collisions with real barcodes while keeping one ID field.

## Store Lookup Rules

- Store lookup is by exact address.
- Android store cache now preserves:
  - `name`
  - optional coordinates
  - `requiresPaidMembership`
- If a store is found remotely by address, it is cached locally.

Key file:

- `android/app/src/main/java/com/example/grocerystoreorganizer/data/local/repository/StoreLookupRepository.kt`

## Commands That Were Used Successfully

### Android

From `android/`:

```bash
./gradlew :app:testDebugUnitTest
./gradlew :app:compileDebugAndroidTestKotlin
```

### Server

From repo root:

```bash
./ai_server/.venv/bin/python -m unittest db_server.tests.test_repository db_server.tests.test_server -v
./ai_server/.venv/bin/python -m db_server.smoke_test
./ai_server/.venv/bin/python -m db_server.smoke_test --disable-ai
```

### Proto Regeneration

From repo root:

```bash
protoc --java_out=lite:android/app/src/main/java -I protos protos/db_service.proto
./db_server/.venv/bin/python -m grpc_tools.protoc -I protos --python_out=db_server --grpc_python_out=db_server --pyi_out=db_server protos/db_service.proto
```

After regenerating Python stubs, fix:

- `db_server/db_service_pb2_grpc.py`

Import must be:

```python
from db_server import db_service_pb2 as db__service__pb2
```

not:

```python
import db_service_pb2 as db__service__pb2
```

## Active Environment Issue

Codex sandbox is still broken in this session with:

```text
bwrap: setting up uid map: Permission denied
```

Host checks looked fine:

- `/proc/sys/kernel/unprivileged_userns_clone = 1`
- `/proc/sys/user/max_user_namespaces > 0`
- `bwrap --version` works
- `unshare -Ur true` works

Conclusion:

- host OS is probably fine
- this is likely a Codex session/runner sandbox issue
- escalated shell execution still works

If starting a new session later, this doc is intended to avoid reloading all of that context.

## Suggested Next Work

Good next tasks, in order:

1. Add optimization filter UI for:
   - allow paid membership required
   - allow loyalty card required
2. Add forward geocoding for manual address entry:
   - keep address required
   - fill coordinates opportunistically when network is available
3. Move more line-item price estimation fully server-side so Android becomes display-only.

