# ai_server

Separate AI service workspace for grocery price tag parsing and model training.

## Setup

Create the virtual environment:

```bash
cd /workspace/github/grocery.io/ai_server
python3 -m venv .venv
source .venv/bin/activate
```

Install CUDA PyTorch first, then the remaining requirements:

```bash
pip install --index-url https://download.pytorch.org/whl/cu124 torch torchvision torchaudio
pip install -r requirements.txt
```

The `requirements.txt` file defaults to CPU wheels for normal installs, following the same pattern as `ipa-gpt`, but the CUDA install above should be run first on machines where you want GPU acceleration.

## Configs

Training uses `cascade-config` directly with layered JSON configs so real paths and machine-specific settings do not need to live in git.

Tracked examples:

- `configs/base.json`
- `configs/local.example.json`

Ignored local configs:

- anything under `run_configs/`

Recommended workflow:

```bash
cd /workspace/github/grocery.io/ai_server
mkdir -p run_configs
cp configs/local.example.json run_configs/local.json
```

Then run training with cascaded configs:

```bash
. .venv/bin/activate
python -m price_tag_ai.train --config configs/base.json --config run_configs/local.json
```

Later configs override earlier ones.

Training pipeline behavior:

- reads labels from `dataset.labels_path` (default `data/labels.json`)
- excludes only `status in {"trashed","skipped"}` and uses flagged samples for ambiguity/unparsable supervision
- deterministically generates train/val JSONL manifests (`dataset.train_manifest`, `dataset.val_manifest`) using `dataset.val_ratio`
- trains a multitask ResNet model (price, unit, net quantity, pack count, variable-weight, ambiguous, unparsable) and saves timestamped checkpoints (for example `best-20260306T120000Z.pt`, `epoch-005-20260306T120000Z.pt`) plus `training_metrics.json` to `train.output_dir`

## Labeling Tool

The preprocessing GUI is a PyQt app that walks a directory of price-tag photos and writes a JSON dataset file.

For OpenAI access, create a local-only secrets file:

```bash
cd /workspace/github/grocery.io/ai_server
cp local.secrets.example.json local.secrets.json
```

Then set:

```json
{
  "openai_api_key": "sk-...",
  "openai_model": "gpt-4.1"
}
```

`local.secrets.json` is ignored by git. `OPENAI_API_KEY` and `OPENAI_MODEL` environment variables still override it.

Run it like this:

```bash
cd /workspace/github/grocery.io/ai_server
. .venv/bin/activate
python -m price_tag_ai.labeler --images-dir /path/to/photos --dataset /path/to/dataset.json
```

Behavior:

- runs an OpenAI connectivity smoke test at startup using your current config/secrets and warns if it fails
- loads images one by one from the directory
- rotates displayed images by 90 degrees for current camera orientation
- compresses/resizes images before OpenAI upload and applies a request timeout so failures surface quickly
- prepopulates fields from an existing dataset entry when present
- otherwise calls OpenAI to prefill numeric fields using structured outputs
- lets you `Submit`, `Skip`, `Trash`, `Back`, and `Next`

The dataset file is a JSON list of records keyed by `image_filename`.
