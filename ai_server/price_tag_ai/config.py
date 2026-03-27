from __future__ import annotations

from pathlib import Path

from cascade_config import CascadeConfig
from pydantic import BaseModel, Field


class AugmentationConfig(BaseModel):
    enabled: bool = True
    rotation_degrees: float = 7.0
    brightness: float = 0.15
    contrast: float = 0.15
    blur_probability: float = 0.2
    blur_kernel_size: int = 3
    blur_sigma_min: float = 0.1
    blur_sigma_max: float = 1.25
    perspective_probability: float = 0.2
    perspective_distortion_scale: float = 0.1
    noise_probability: float = 0.25
    noise_std: float = 0.02


class DatasetConfig(BaseModel):
    labels_path: str = "data/labels.json"
    train_manifest: str = ""
    val_manifest: str = ""
    image_root: str = ""
    val_ratio: float = 0.2
    min_train_samples: int = 1
    num_workers: int = 4
    augmentation: AugmentationConfig = Field(default_factory=AugmentationConfig)


class ModelConfig(BaseModel):
    backbone: str = "mobilenet_v3_small"
    hf_model_name: str = "google/vit-base-patch16-224-in21k"
    pretrained: bool = True
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


class WandbConfig(BaseModel):
    enabled: bool = False
    entity: str = ""
    project: str = ""


class AppConfig(BaseModel):
    experiment_name: str = "price-tag-baseline"
    dataset: DatasetConfig = Field(default_factory=DatasetConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    optimizer: OptimizerConfig = Field(default_factory=OptimizerConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    train: TrainConfig = Field(default_factory=TrainConfig)
    wandb: WandbConfig = Field(default_factory=WandbConfig)


def load_config(*config_paths: str | Path) -> AppConfig:
    cascade = CascadeConfig()
    for config_path in config_paths:
        if config_path:
            cascade.add_json(str(config_path))
    return AppConfig.model_validate(cascade.parse())
