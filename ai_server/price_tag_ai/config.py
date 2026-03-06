from __future__ import annotations

from pathlib import Path

from cascade_config import CascadeConfig
from pydantic import BaseModel, Field


class DatasetConfig(BaseModel):
    labels_path: str = "data/labels.json"
    train_manifest: str = ""
    val_manifest: str = ""
    image_root: str = ""
    val_ratio: float = 0.2
    min_train_samples: int = 1
    num_workers: int = 4


class ModelConfig(BaseModel):
    backbone: str = "resnet18"
    pretrained: bool = False
    image_size: int = 224
    dropout: float = 0.1


class OptimizerConfig(BaseModel):
    name: str = "adamw"
    lr: float = 3e-4
    weight_decay: float = 1e-4


class SchedulerConfig(BaseModel):
    name: str = "cosine"
    min_lr: float = 1e-6


class TrainConfig(BaseModel):
    seed: int = 1337
    device: str = "cuda"
    batch_size: int = 32
    epochs: int = 10
    output_dir: str = "outputs/default"
    log_every_n_steps: int = 0
    save_every_n_epochs: int = 1


class AppConfig(BaseModel):
    experiment_name: str = "price-tag-baseline"
    dataset: DatasetConfig = Field(default_factory=DatasetConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    optimizer: OptimizerConfig = Field(default_factory=OptimizerConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    train: TrainConfig = Field(default_factory=TrainConfig)


def load_config(*config_paths: str | Path) -> AppConfig:
    cascade = CascadeConfig()
    for config_path in config_paths:
        if config_path:
            cascade.add_json(str(config_path))
    return AppConfig.model_validate(cascade.parse())
