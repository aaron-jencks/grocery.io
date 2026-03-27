from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import random
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from PIL import Image
from torch import nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import (
    MobileNet_V3_Large_Weights,
    MobileNet_V3_Small_Weights,
    ResNet18_Weights,
    ResNet34_Weights,
    ResNet50_Weights,
    mobilenet_v3_large,
    mobilenet_v3_small,
    resnet18,
    resnet34,
    resnet50,
)

from price_tag_ai.config import AppConfig, AugmentationConfig, load_config
from price_tag_ai.dataset import PriceTagDatasetStore


UNITS = ["OZ", "LB", "ITEM", "KG", "G", "LIT", "ML", "GAL", "QT", "PT", "TSP", "TBSP", "FL_OZ", "CUP"]
UNIT_TO_INDEX = {unit: index for index, unit in enumerate(UNITS)}


@dataclass(frozen=True)
class ManifestRecord:
    image_filename: str
    price: float | None
    net_quantity: float | None
    pack_count: float | None
    quantity_unit: str | None
    is_variable_weight: bool
    is_ambiguous: bool
    is_unparsable: bool
    upc_present: bool


class PriceTagTorchDataset(Dataset):
    def __init__(
        self,
        records: list[ManifestRecord],
        image_root: Path,
        image_size: int,
        train: bool,
        augmentation: AugmentationConfig,
    ):
        self.records = records
        self.image_root = image_root
        self.transform = self._build_transform(
            image_size=image_size,
            train=train,
            augmentation=augmentation,
        )

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> dict[str, Any]:
        record = self.records[index]
        image_path = self.image_root / record.image_filename
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            image_tensor = self.transform(image)

        quantity_unit_index = UNIT_TO_INDEX.get(record.quantity_unit or "", -100)
        return {
            "image": image_tensor,
            "price": torch.tensor(
                0.0 if record.price is None else float(record.price),
                dtype=torch.float32,
            ),
            "price_mask": torch.tensor(record.price is not None, dtype=torch.bool),
            "net_quantity": torch.tensor(
                0.0 if record.net_quantity is None else float(record.net_quantity),
                dtype=torch.float32,
            ),
            "net_quantity_mask": torch.tensor(record.net_quantity is not None, dtype=torch.bool),
            "pack_count": torch.tensor(
                0.0 if record.pack_count is None else float(record.pack_count),
                dtype=torch.float32,
            ),
            "pack_count_mask": torch.tensor(record.pack_count is not None, dtype=torch.bool),
            "quantity_unit_index": torch.tensor(quantity_unit_index, dtype=torch.long),
            "quantity_unit_mask": torch.tensor(quantity_unit_index >= 0, dtype=torch.bool),
            "is_variable_weight": torch.tensor(
                1.0 if record.is_variable_weight else 0.0,
                dtype=torch.float32,
            ),
            "is_ambiguous": torch.tensor(
                1.0 if record.is_ambiguous else 0.0,
                dtype=torch.float32,
            ),
            "is_unparsable": torch.tensor(
                1.0 if record.is_unparsable else 0.0,
                dtype=torch.float32,
            ),
            "upc_present": torch.tensor(
                1.0 if record.upc_present else 0.0,
                dtype=torch.float32,
            ),
        }

    def _build_transform(
        self,
        image_size: int,
        train: bool,
        augmentation: AugmentationConfig,
    ) -> transforms.Compose:
        augment = build_augmentations(augmentation) if train else []
        tensor_augment = build_tensor_augmentations(augmentation) if train else []
        return transforms.Compose(
            [
                transforms.Resize((image_size, image_size)),
                *augment,
                transforms.ToTensor(),
                *tensor_augment,
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ]
        )


class AddGaussianNoise(nn.Module):
    def __init__(self, std: float):
        super().__init__()
        self.std = std

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        noise = torch.randn_like(tensor) * self.std
        return torch.clamp(tensor + noise, 0.0, 1.0)


def build_augmentations(augmentation: AugmentationConfig) -> list[Any]:
    if not augmentation.enabled:
        return []
    image_augmentations: list[Any] = [
        transforms.RandomRotation(degrees=augmentation.rotation_degrees),
        transforms.ColorJitter(
            brightness=augmentation.brightness,
            contrast=augmentation.contrast,
        ),
    ]
    if augmentation.perspective_probability > 0.0:
        image_augmentations.append(
            transforms.RandomPerspective(
                distortion_scale=augmentation.perspective_distortion_scale,
                p=augmentation.perspective_probability,
            )
        )
    if augmentation.blur_probability > 0.0:
        image_augmentations.append(
            transforms.RandomApply(
                [
                    transforms.GaussianBlur(
                        kernel_size=augmentation.blur_kernel_size,
                        sigma=(augmentation.blur_sigma_min, augmentation.blur_sigma_max),
                    )
                ],
                p=augmentation.blur_probability,
            )
        )
    return image_augmentations


def build_tensor_augmentations(augmentation: AugmentationConfig) -> list[Any]:
    if (
        not augmentation.enabled
        or augmentation.noise_probability <= 0.0
        or augmentation.noise_std <= 0.0
    ):
        return []
    return [
        transforms.RandomApply(
            [AddGaussianNoise(std=augmentation.noise_std)],
            p=augmentation.noise_probability,
        )
    ]


class PriceTagModel(nn.Module):
    def __init__(self, backbone: str, dropout: float, pretrained: bool):
        super().__init__()
        self.encoder, feature_dim = self._build_backbone(backbone, pretrained)
        self.dropout = nn.Dropout(dropout)

        self.head_price = nn.Linear(feature_dim, 1)
        self.head_net_quantity = nn.Linear(feature_dim, 1)
        self.head_pack_count = nn.Linear(feature_dim, 1)
        self.head_unit = nn.Linear(feature_dim, len(UNITS))
        self.head_variable_weight = nn.Linear(feature_dim, 1)
        self.head_ambiguous = nn.Linear(feature_dim, 1)
        self.head_unparsable = nn.Linear(feature_dim, 1)
        self.head_upc_present = nn.Linear(feature_dim, 1)

    def forward(self, images: torch.Tensor) -> dict[str, torch.Tensor]:
        features = self.encoder(images)
        features = self.dropout(features)
        return {
            "price": self.head_price(features).squeeze(-1),
            "net_quantity": self.head_net_quantity(features).squeeze(-1),
            "pack_count": self.head_pack_count(features).squeeze(-1),
            "unit_logits": self.head_unit(features),
            "variable_weight_logit": self.head_variable_weight(features).squeeze(-1),
            "ambiguous_logit": self.head_ambiguous(features).squeeze(-1),
            "unparsable_logit": self.head_unparsable(features).squeeze(-1),
            "upc_present_logit": self.head_upc_present(features).squeeze(-1),
        }

    def _build_backbone(
        self,
        backbone: str,
        pretrained: bool,
    ) -> tuple[nn.Module, int]:
        if backbone == "resnet18":
            net = resnet18(weights=ResNet18_Weights.DEFAULT if pretrained else None)
            feature_dim = net.fc.in_features
            net.fc = nn.Identity()
        elif backbone == "resnet34":
            net = resnet34(weights=ResNet34_Weights.DEFAULT if pretrained else None)
            feature_dim = net.fc.in_features
            net.fc = nn.Identity()
        elif backbone == "resnet50":
            net = resnet50(weights=ResNet50_Weights.DEFAULT if pretrained else None)
            feature_dim = net.fc.in_features
            net.fc = nn.Identity()
        elif backbone == "mobilenet_v3_small":
            net = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.DEFAULT if pretrained else None)
            feature_dim = net.classifier[0].in_features
            net.classifier = nn.Identity()
        elif backbone == "mobilenet_v3_large":
            net = mobilenet_v3_large(weights=MobileNet_V3_Large_Weights.DEFAULT if pretrained else None)
            feature_dim = net.classifier[0].in_features
            net.classifier = nn.Identity()
        else:
            raise ValueError(f"Unsupported backbone: {backbone}")

        return net, feature_dim


def build_run_timestamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def init_wandb_run(config: AppConfig, run_name: str):
    if not config.wandb.enabled:
        return None
    if not config.wandb.project:
        raise ValueError("wandb.project is required when wandb.enabled=true")
    if not config.wandb.entity:
        raise ValueError("wandb.entity is required when wandb.enabled=true")
    import wandb

    return wandb.init(
        entity=config.wandb.entity,
        project=config.wandb.project,
        name=run_name,
        config=config.model_dump(mode="json"),
    )


def configure_wandb_env(config: AppConfig, run_name: str) -> None:
    if not config.wandb.enabled:
        return
    if not config.wandb.project:
        raise ValueError("wandb.project is required when wandb.enabled=true")
    if not config.wandb.entity:
        raise ValueError("wandb.entity is required when wandb.enabled=true")
    os.environ["WANDB_PROJECT"] = config.wandb.project
    os.environ["WANDB_ENTITY"] = config.wandb.entity
    os.environ["WANDB_NAME"] = run_name


def wandb_log(config: AppConfig, payload: dict[str, float], step: int | None = None) -> None:
    if not config.wandb.enabled:
        return
    import wandb

    wandb.log(payload, step=step)


def finish_wandb_run(config: AppConfig) -> None:
    if not config.wandb.enabled:
        return
    import wandb

    wandb.finish()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        dest="configs",
        action="append",
        required=True,
        help="JSON config file. Pass multiple times to layer configs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(*args.configs)
    run_training(config)


def run_training(config: AppConfig) -> None:
    set_seed(config.train.seed)

    output_dir = Path(config.train.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_timestamp = build_run_timestamp()
    wandb_run = init_wandb_run(config, run_timestamp)

    train_manifest = Path(config.dataset.train_manifest)
    val_manifest = Path(config.dataset.val_manifest)
    generate_splits(config, train_manifest, val_manifest)

    image_root = Path(config.dataset.image_root)
    train_records = read_manifest(train_manifest)
    val_records = read_manifest(val_manifest)
    if len(train_records) < config.dataset.min_train_samples:
        raise ValueError(
            f"Not enough training samples ({len(train_records)}). "
            f"Require at least {config.dataset.min_train_samples}."
        )

    train_dataset = PriceTagTorchDataset(
        records=train_records,
        image_root=image_root,
        image_size=config.model.image_size,
        train=True,
        augmentation=config.dataset.augmentation,
    )
    val_dataset = PriceTagTorchDataset(
        records=val_records,
        image_root=image_root,
        image_size=config.model.image_size,
        train=False,
        augmentation=config.dataset.augmentation,
    )
    current_num_workers = resolve_num_workers(config.dataset.num_workers)
    train_loader, val_loader = build_loaders(
        train_dataset=train_dataset,
        val_dataset=val_dataset,
        batch_size=config.train.batch_size,
        num_workers=current_num_workers,
    )

    device = resolve_device(config.train.device)
    model = PriceTagModel(
        backbone=config.model.backbone,
        dropout=config.model.dropout,
        pretrained=config.model.pretrained,
    ).to(device)
    optimizer = build_optimizer(model, config)
    scheduler = build_scheduler(optimizer, config)
    binary_pos_weights = compute_binary_pos_weights(train_records)

    print(f"Experiment: {config.experiment_name}")
    print(f"Device: {device}")
    print(f"Train samples: {len(train_dataset)}")
    print(f"Val samples: {len(val_dataset)}")
    print(f"DataLoader workers: {current_num_workers}")
    print(f"Output dir: {output_dir}")
    print(
        "Binary prevalence (train positives / total): "
        f"var={count_positive(train_records, 'is_variable_weight')}/{len(train_records)}, "
        f"amb={count_positive(train_records, 'is_ambiguous')}/{len(train_records)}, "
        f"unpars={count_positive(train_records, 'is_unparsable')}/{len(train_records)}, "
        f"upc={count_positive(train_records, 'upc_present')}/{len(train_records)}"
    )
    print(
        "Binary pos_weight: "
        f"var={binary_pos_weights['is_variable_weight']:.3f}, "
        f"amb={binary_pos_weights['is_ambiguous']:.3f}, "
        f"unpars={binary_pos_weights['is_unparsable']:.3f}, "
        f"upc={binary_pos_weights['upc_present']:.3f}"
    )
    best_checkpoint_path = output_dir / f"best-{run_timestamp}.pt"

    best_val_loss = float("inf")
    history: list[dict[str, float]] = []

    try:
        for epoch in range(1, config.train.epochs + 1):
            epoch_start = time.perf_counter()
            try:
                train_metrics = run_epoch(
                    model=model,
                    loader=train_loader,
                    optimizer=optimizer,
                    device=device,
                    train=True,
                    log_every_n_steps=config.train.log_every_n_steps,
                    binary_pos_weights=binary_pos_weights,
                )
                val_metrics = run_epoch(
                    model=model,
                    loader=val_loader,
                    optimizer=None,
                    device=device,
                    train=False,
                    log_every_n_steps=config.train.log_every_n_steps,
                    binary_pos_weights=binary_pos_weights,
                )
            except PermissionError:
                if current_num_workers <= 0:
                    raise
                print(
                    "DataLoader multiprocessing failed in this environment; "
                    "falling back to num_workers=0.",
                )
                current_num_workers = 0
                train_loader, val_loader = build_loaders(
                    train_dataset=train_dataset,
                    val_dataset=val_dataset,
                    batch_size=config.train.batch_size,
                    num_workers=current_num_workers,
                )
                train_metrics = run_epoch(
                    model=model,
                    loader=train_loader,
                    optimizer=optimizer,
                    device=device,
                    train=True,
                    log_every_n_steps=config.train.log_every_n_steps,
                    binary_pos_weights=binary_pos_weights,
                )
                val_metrics = run_epoch(
                    model=model,
                    loader=val_loader,
                    optimizer=None,
                    device=device,
                    train=False,
                    log_every_n_steps=config.train.log_every_n_steps,
                    binary_pos_weights=binary_pos_weights,
                )
            epoch_seconds = time.perf_counter() - epoch_start
            history.append({
                "epoch": float(epoch),
                "train_loss": train_metrics["loss"],
                "val_loss": val_metrics["loss"],
                "val_price_mae": val_metrics["price_mae"],
                "val_price_rmse": val_metrics["price_rmse"],
                "val_net_quantity_mae": val_metrics["net_quantity_mae"],
                "val_net_quantity_rmse": val_metrics["net_quantity_rmse"],
                "val_pack_count_mae": val_metrics["pack_count_mae"],
                "val_pack_count_rmse": val_metrics["pack_count_rmse"],
                "val_unit_accuracy": val_metrics["unit_accuracy"],
                "val_variable_weight_accuracy": val_metrics["variable_weight_accuracy"],
                "val_variable_weight_precision": val_metrics["variable_weight_precision"],
                "val_variable_weight_recall": val_metrics["variable_weight_recall"],
                "val_variable_weight_f1": val_metrics["variable_weight_f1"],
                "val_ambiguous_accuracy": val_metrics["ambiguous_accuracy"],
                "val_ambiguous_precision": val_metrics["ambiguous_precision"],
                "val_ambiguous_recall": val_metrics["ambiguous_recall"],
                "val_ambiguous_f1": val_metrics["ambiguous_f1"],
                "val_unparsable_accuracy": val_metrics["unparsable_accuracy"],
                "val_unparsable_precision": val_metrics["unparsable_precision"],
                "val_unparsable_recall": val_metrics["unparsable_recall"],
                "val_unparsable_f1": val_metrics["unparsable_f1"],
                "val_upc_present_accuracy": val_metrics["upc_present_accuracy"],
                "val_upc_present_precision": val_metrics["upc_present_precision"],
                "val_upc_present_recall": val_metrics["upc_present_recall"],
                "val_upc_present_f1": val_metrics["upc_present_f1"],
            })

            wandb_log(
                config,
                {
                    "epoch": float(epoch),
                    "train/loss": train_metrics["loss"],
                    "val/loss": val_metrics["loss"],
                    "val/unit_accuracy": val_metrics["unit_accuracy"],
                    "val/price_mae": val_metrics["price_mae"],
                    "val/price_rmse": val_metrics["price_rmse"],
                    "val/net_quantity_mae": val_metrics["net_quantity_mae"],
                    "val/net_quantity_rmse": val_metrics["net_quantity_rmse"],
                    "val/pack_count_mae": val_metrics["pack_count_mae"],
                    "val/pack_count_rmse": val_metrics["pack_count_rmse"],
                    "val/variable_weight_f1": val_metrics["variable_weight_f1"],
                    "val/ambiguous_f1": val_metrics["ambiguous_f1"],
                    "val/unparsable_f1": val_metrics["unparsable_f1"],
                    "val/upc_present_f1": val_metrics["upc_present_f1"],
                    "train/lr": optimizer.param_groups[0]["lr"],
                    "train/epoch_seconds": epoch_seconds,
                },
                step=epoch,
            )

            print(
                f"[epoch {epoch}] "
                f"train_loss={train_metrics['loss']:.4f} "
                f"val_loss={val_metrics['loss']:.4f} "
                f"unit_acc={val_metrics['unit_accuracy']:.3f} "
                f"price_mae={val_metrics['price_mae']:.3f} "
                f"lr={optimizer.param_groups[0]['lr']:.7f} "
                f"secs={epoch_seconds:.2f}"
            )
            print(
                "  val_regression "
                f"price_rmse={val_metrics['price_rmse']:.3f} "
                f"net_mae={val_metrics['net_quantity_mae']:.3f} net_rmse={val_metrics['net_quantity_rmse']:.3f} "
                f"pack_mae={val_metrics['pack_count_mae']:.3f} pack_rmse={val_metrics['pack_count_rmse']:.3f}"
            )
            print(
                "  val_binary "
                f"var_f1={val_metrics['variable_weight_f1']:.3f} "
                f"amb_f1={val_metrics['ambiguous_f1']:.3f} "
                f"unpars_f1={val_metrics['unparsable_f1']:.3f} "
                f"upc_f1={val_metrics['upc_present_f1']:.3f}"
            )

            if val_metrics["loss"] < best_val_loss:
                best_val_loss = val_metrics["loss"]
                save_checkpoint(
                    best_checkpoint_path,
                    model,
                    optimizer,
                    scheduler,
                    epoch,
                    config,
                    val_metrics,
                    alias_paths=[output_dir / "best.pt", output_dir / "best_custom.pt"],
                )
            if epoch % config.train.save_every_n_epochs == 0:
                save_checkpoint(
                    output_dir / f"epoch-{epoch:03d}-{run_timestamp}.pt",
                    model,
                    optimizer,
                    scheduler,
                    epoch,
                    config,
                    val_metrics,
                )
            scheduler.step()

        print_final_summary(history)
        write_training_artifacts(output_dir, config, history)
        print("Training complete.")
    finally:
        if wandb_run is not None:
            finish_wandb_run(config)


def run_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: AdamW | None,
    device: torch.device,
    train: bool,
    log_every_n_steps: int,
    binary_pos_weights: dict[str, float],
) -> dict[str, float]:
    if train:
        model.train()
    else:
        model.eval()

    total_loss = 0.0
    batches = 0
    price_abs_sum = 0.0
    price_sq_sum = 0.0
    price_count = 0.0
    net_abs_sum = 0.0
    net_sq_sum = 0.0
    net_count = 0.0
    pack_abs_sum = 0.0
    pack_sq_sum = 0.0
    pack_count = 0.0
    unit_correct = 0.0
    unit_total = 0.0
    variable_tp = variable_fp = variable_fn = variable_tn = 0.0
    ambiguous_tp = ambiguous_fp = ambiguous_fn = ambiguous_tn = 0.0
    unparsable_tp = unparsable_fp = unparsable_fn = unparsable_tn = 0.0
    upc_tp = upc_fp = upc_fn = upc_tn = 0.0

    context = torch.enable_grad() if train else torch.no_grad()
    with context:
        for step, batch in enumerate(loader, start=1):
            images = batch["image"].to(device)
            outputs = model(images)

            losses = []
            losses.append(masked_mse(outputs["price"], batch["price"].to(device), batch["price_mask"].to(device)))
            losses.append(
                masked_mse(
                    outputs["net_quantity"],
                    batch["net_quantity"].to(device),
                    batch["net_quantity_mask"].to(device),
                )
            )
            losses.append(
                masked_mse(
                    outputs["pack_count"],
                    batch["pack_count"].to(device),
                    batch["pack_count_mask"].to(device),
                )
            )
            losses.append(
                F.cross_entropy(
                    outputs["unit_logits"],
                    batch["quantity_unit_index"].to(device),
                    ignore_index=-100,
                )
            )
            losses.append(
                F.binary_cross_entropy_with_logits(
                    outputs["variable_weight_logit"],
                    batch["is_variable_weight"].to(device),
                    pos_weight=torch.tensor(
                        binary_pos_weights["is_variable_weight"],
                        device=device,
                        dtype=torch.float32,
                    ),
                )
            )
            losses.append(
                F.binary_cross_entropy_with_logits(
                    outputs["ambiguous_logit"],
                    batch["is_ambiguous"].to(device),
                    pos_weight=torch.tensor(
                        binary_pos_weights["is_ambiguous"],
                        device=device,
                        dtype=torch.float32,
                    ),
                )
            )
            losses.append(
                F.binary_cross_entropy_with_logits(
                    outputs["unparsable_logit"],
                    batch["is_unparsable"].to(device),
                    pos_weight=torch.tensor(
                        binary_pos_weights["is_unparsable"],
                        device=device,
                        dtype=torch.float32,
                    ),
                )
            )
            losses.append(
                F.binary_cross_entropy_with_logits(
                    outputs["upc_present_logit"],
                    batch["upc_present"].to(device),
                    pos_weight=torch.tensor(
                        binary_pos_weights["upc_present"],
                        device=device,
                        dtype=torch.float32,
                    ),
                )
            )
            loss = sum(losses)

            if train and optimizer is not None:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()

            total_loss += float(loss.detach().cpu().item())
            batches += 1

            step_metrics = compute_batch_metrics(batch, outputs, device)
            price_abs_sum += step_metrics["price_abs_sum"]
            price_sq_sum += step_metrics["price_sq_sum"]
            price_count += step_metrics["price_count"]
            net_abs_sum += step_metrics["net_abs_sum"]
            net_sq_sum += step_metrics["net_sq_sum"]
            net_count += step_metrics["net_count"]
            pack_abs_sum += step_metrics["pack_abs_sum"]
            pack_sq_sum += step_metrics["pack_sq_sum"]
            pack_count += step_metrics["pack_count"]
            unit_correct += step_metrics["unit_correct"]
            unit_total += step_metrics["unit_total"]
            variable_tp += step_metrics["variable_tp"]
            variable_fp += step_metrics["variable_fp"]
            variable_fn += step_metrics["variable_fn"]
            variable_tn += step_metrics["variable_tn"]
            ambiguous_tp += step_metrics["ambiguous_tp"]
            ambiguous_fp += step_metrics["ambiguous_fp"]
            ambiguous_fn += step_metrics["ambiguous_fn"]
            ambiguous_tn += step_metrics["ambiguous_tn"]
            unparsable_tp += step_metrics["unparsable_tp"]
            unparsable_fp += step_metrics["unparsable_fp"]
            unparsable_fn += step_metrics["unparsable_fn"]
            unparsable_tn += step_metrics["unparsable_tn"]
            upc_tp += step_metrics["upc_tp"]
            upc_fp += step_metrics["upc_fp"]
            upc_fn += step_metrics["upc_fn"]
            upc_tn += step_metrics["upc_tn"]

            if train and log_every_n_steps > 0 and step % log_every_n_steps == 0:
                print(f"  step {step}: loss={float(loss.item()):.4f}")

    variable_stats = binary_stats(variable_tp, variable_fp, variable_fn, variable_tn)
    ambiguous_stats = binary_stats(ambiguous_tp, ambiguous_fp, ambiguous_fn, ambiguous_tn)
    unparsable_stats = binary_stats(unparsable_tp, unparsable_fp, unparsable_fn, unparsable_tn)
    upc_stats = binary_stats(upc_tp, upc_fp, upc_fn, upc_tn)

    return {
        "loss": total_loss / max(1, batches),
        "price_mae": price_abs_sum / max(1.0, price_count),
        "price_rmse": (price_sq_sum / max(1.0, price_count)) ** 0.5,
        "net_quantity_mae": net_abs_sum / max(1.0, net_count),
        "net_quantity_rmse": (net_sq_sum / max(1.0, net_count)) ** 0.5,
        "pack_count_mae": pack_abs_sum / max(1.0, pack_count),
        "pack_count_rmse": (pack_sq_sum / max(1.0, pack_count)) ** 0.5,
        "unit_accuracy": unit_correct / max(1.0, unit_total),
        "variable_weight_accuracy": variable_stats["accuracy"],
        "variable_weight_precision": variable_stats["precision"],
        "variable_weight_recall": variable_stats["recall"],
        "variable_weight_f1": variable_stats["f1"],
        "ambiguous_accuracy": ambiguous_stats["accuracy"],
        "ambiguous_precision": ambiguous_stats["precision"],
        "ambiguous_recall": ambiguous_stats["recall"],
        "ambiguous_f1": ambiguous_stats["f1"],
        "unparsable_accuracy": unparsable_stats["accuracy"],
        "unparsable_precision": unparsable_stats["precision"],
        "unparsable_recall": unparsable_stats["recall"],
        "unparsable_f1": unparsable_stats["f1"],
        "upc_present_accuracy": upc_stats["accuracy"],
        "upc_present_precision": upc_stats["precision"],
        "upc_present_recall": upc_stats["recall"],
        "upc_present_f1": upc_stats["f1"],
    }


def build_loaders(
    train_dataset: Dataset,
    val_dataset: Dataset,
    batch_size: int,
    num_workers: int,
) -> tuple[DataLoader, DataLoader]:
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=max(0, int(num_workers)),
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=max(0, int(num_workers)),
    )
    return train_loader, val_loader


def compute_batch_metrics(
    batch: dict[str, torch.Tensor],
    outputs: dict[str, torch.Tensor],
    device: torch.device,
) -> dict[str, float]:
    price_target = batch["price"].to(device)
    price_mask = batch["price_mask"].to(device)
    price_pred = outputs["price"]
    price_err = (price_pred - price_target)
    price_abs_sum = torch.abs(price_err)[price_mask].sum().item() if price_mask.any() else 0.0
    price_sq_sum = (price_err * price_err)[price_mask].sum().item() if price_mask.any() else 0.0
    price_count = float(price_mask.sum().item())

    net_target = batch["net_quantity"].to(device)
    net_mask = batch["net_quantity_mask"].to(device)
    net_pred = outputs["net_quantity"]
    net_err = (net_pred - net_target)
    net_abs_sum = torch.abs(net_err)[net_mask].sum().item() if net_mask.any() else 0.0
    net_sq_sum = (net_err * net_err)[net_mask].sum().item() if net_mask.any() else 0.0
    net_count = float(net_mask.sum().item())

    pack_target = batch["pack_count"].to(device)
    pack_mask = batch["pack_count_mask"].to(device)
    pack_pred = outputs["pack_count"]
    pack_err = (pack_pred - pack_target)
    pack_abs_sum = torch.abs(pack_err)[pack_mask].sum().item() if pack_mask.any() else 0.0
    pack_sq_sum = (pack_err * pack_err)[pack_mask].sum().item() if pack_mask.any() else 0.0
    pack_count = float(pack_mask.sum().item())

    unit_target = batch["quantity_unit_index"].to(device)
    unit_mask = batch["quantity_unit_mask"].to(device)
    unit_pred = outputs["unit_logits"].argmax(dim=1)
    unit_correct = (unit_pred[unit_mask] == unit_target[unit_mask]).sum().item() if unit_mask.any() else 0.0
    unit_total = float(unit_mask.sum().item())

    variable_tp, variable_fp, variable_fn, variable_tn = confusion_counts(
        pred=(torch.sigmoid(outputs["variable_weight_logit"]) >= 0.5).float(),
        target=batch["is_variable_weight"].to(device),
    )
    ambiguous_tp, ambiguous_fp, ambiguous_fn, ambiguous_tn = confusion_counts(
        pred=(torch.sigmoid(outputs["ambiguous_logit"]) >= 0.5).float(),
        target=batch["is_ambiguous"].to(device),
    )
    unparsable_tp, unparsable_fp, unparsable_fn, unparsable_tn = confusion_counts(
        pred=(torch.sigmoid(outputs["unparsable_logit"]) >= 0.5).float(),
        target=batch["is_unparsable"].to(device),
    )
    upc_tp, upc_fp, upc_fn, upc_tn = confusion_counts(
        pred=(torch.sigmoid(outputs["upc_present_logit"]) >= 0.5).float(),
        target=batch["upc_present"].to(device),
    )

    return {
        "price_abs_sum": float(price_abs_sum),
        "price_sq_sum": float(price_sq_sum),
        "price_count": price_count,
        "net_abs_sum": float(net_abs_sum),
        "net_sq_sum": float(net_sq_sum),
        "net_count": net_count,
        "pack_abs_sum": float(pack_abs_sum),
        "pack_sq_sum": float(pack_sq_sum),
        "pack_count": pack_count,
        "unit_correct": float(unit_correct),
        "unit_total": unit_total,
        "variable_tp": variable_tp,
        "variable_fp": variable_fp,
        "variable_fn": variable_fn,
        "variable_tn": variable_tn,
        "ambiguous_tp": ambiguous_tp,
        "ambiguous_fp": ambiguous_fp,
        "ambiguous_fn": ambiguous_fn,
        "ambiguous_tn": ambiguous_tn,
        "unparsable_tp": unparsable_tp,
        "unparsable_fp": unparsable_fp,
        "unparsable_fn": unparsable_fn,
        "unparsable_tn": unparsable_tn,
        "upc_tp": upc_tp,
        "upc_fp": upc_fp,
        "upc_fn": upc_fn,
        "upc_tn": upc_tn,
    }


def confusion_counts(pred: torch.Tensor, target: torch.Tensor) -> tuple[float, float, float, float]:
    tp = ((pred == 1.0) & (target == 1.0)).sum().item()
    fp = ((pred == 1.0) & (target == 0.0)).sum().item()
    fn = ((pred == 0.0) & (target == 1.0)).sum().item()
    tn = ((pred == 0.0) & (target == 0.0)).sum().item()
    return float(tp), float(fp), float(fn), float(tn)


def binary_stats(tp: float, fp: float, fn: float, tn: float) -> dict[str, float]:
    precision = tp / max(1.0, tp + fp)
    recall = tp / max(1.0, tp + fn)
    f1 = (2.0 * precision * recall) / max(1e-12, precision + recall)
    accuracy = (tp + tn) / max(1.0, tp + tn + fp + fn)
    return {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }


def masked_mse(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    if mask.sum().item() == 0:
        return pred.new_tensor(0.0)
    return F.mse_loss(pred[mask], target[mask])


def build_optimizer(model: nn.Module, config: AppConfig) -> AdamW:
    if config.optimizer.name.lower() != "adamw":
        raise ValueError(f"Unsupported optimizer: {config.optimizer.name}")
    return AdamW(
        model.parameters(),
        lr=config.optimizer.lr,
        weight_decay=config.optimizer.weight_decay,
    )


def build_scheduler(optimizer: AdamW, config: AppConfig) -> CosineAnnealingLR:
    name = config.scheduler.name.lower()
    if name != "cosine":
        raise ValueError(f"Unsupported scheduler: {config.scheduler.name}")
    return CosineAnnealingLR(
        optimizer,
        T_max=max(1, config.train.epochs),
        eta_min=config.scheduler.min_lr,
    )


def generate_splits(config: AppConfig, train_manifest: Path, val_manifest: Path) -> None:
    records = collect_eligible_records(config)
    if not records:
        raise ValueError("No eligible labeled records found for training.")

    val_count = int(round(len(records) * config.dataset.val_ratio))
    if len(records) > 1:
        val_count = max(1, min(val_count, len(records) - 1))
    else:
        val_count = 0

    train_records, val_records = split_records_with_flag_coverage(
        records=records,
        val_count=val_count,
        seed=config.train.seed,
    )
    write_manifest(train_manifest, train_records)
    write_manifest(val_manifest, val_records)

    print(f"Generated manifests -> train={len(train_records)} val={len(val_records)}")
    print(
        "  flag_coverage "
        f"train(var={count_positive(train_records, 'is_variable_weight')}, "
        f"amb={count_positive(train_records, 'is_ambiguous')}, "
        f"unpars={count_positive(train_records, 'is_unparsable')}) "
        f"val(var={count_positive(val_records, 'is_variable_weight')}, "
        f"amb={count_positive(val_records, 'is_ambiguous')}, "
        f"unpars={count_positive(val_records, 'is_unparsable')})"
    )


def collect_eligible_records(config: AppConfig) -> list[ManifestRecord]:
    labels_path = Path(config.dataset.labels_path)
    image_root = Path(config.dataset.image_root)
    store = PriceTagDatasetStore(labels_path)
    records: list[ManifestRecord] = []
    for record in store.values():
        if record.status in {"trashed", "skipped"}:
            continue
        quantity_unit = normalize_quantity_unit(record.quantity_unit)
        if quantity_unit is not None and quantity_unit not in UNIT_TO_INDEX:
            continue
        if not (image_root / record.image_filename).exists():
            continue

        records.append(
            ManifestRecord(
                image_filename=record.image_filename,
                price=record.price,
                net_quantity=record.net_quantity,
                pack_count=record.pack_count,
                quantity_unit=quantity_unit,
                is_variable_weight=bool(record.is_variable_weight),
                is_ambiguous=bool(record.is_ambiguous),
                is_unparsable=bool(record.is_unparsable),
                upc_present=bool(record.upc_present),
            )
        )
    return records


def normalize_quantity_unit(value: str | None) -> str | None:
    if value is None:
        return None
    upper = value.strip().upper()
    if upper == "EA":
        return "ITEM"
    return upper


def split_records_with_flag_coverage(
    records: list[ManifestRecord],
    val_count: int,
    seed: int,
) -> tuple[list[ManifestRecord], list[ManifestRecord]]:
    if not records:
        return [], []
    if val_count <= 0:
        return records[:], []

    rng = random.Random(seed)
    indices = list(range(len(records)))
    rng.shuffle(indices)

    required_flags = [
        "is_variable_weight",
        "is_ambiguous",
        "is_unparsable",
    ]
    selected_for_val: list[int] = []

    # Ensure each flag has at least one positive in val when possible (>=2 total positives).
    for flag in required_flags:
        positives = [i for i in indices if bool(getattr(records[i], flag))]
        if len(positives) < 2:
            continue
        pick = next((i for i in positives if i not in selected_for_val), positives[0])
        if pick not in selected_for_val:
            selected_for_val.append(pick)

    if len(selected_for_val) > val_count:
        selected_for_val = selected_for_val[:val_count]

    remaining = [i for i in indices if i not in selected_for_val]
    need = val_count - len(selected_for_val)
    if need > 0:
        selected_for_val.extend(remaining[:need])

    selected_set = set(selected_for_val)
    required_flags = [
        "is_variable_weight",
        "is_ambiguous",
        "is_unparsable",
    ]
    enforce_two_way_flag_coverage(records, selected_set, required_flags, rng)

    val_records = [records[i] for i in indices if i in selected_set]
    train_records = [records[i] for i in indices if i not in selected_set]
    return train_records, val_records


def count_positive(records: list[ManifestRecord], flag: str) -> int:
    return sum(1 for record in records if bool(getattr(record, flag)))


def enforce_two_way_flag_coverage(
    records: list[ManifestRecord],
    val_index_set: set[int],
    flags: list[str],
    rng: random.Random,
) -> None:
    all_indices = set(range(len(records)))
    for flag in flags:
        positives = [i for i in all_indices if bool(getattr(records[i], flag))]
        if len(positives) < 2:
            continue

        val_pos = [i for i in positives if i in val_index_set]
        train_pos = [i for i in positives if i not in val_index_set]

        if not val_pos and len(train_pos) > 1:
            move_to_val = rng.choice(train_pos)
            move_to_train = choose_swap_candidate(
                records=records,
                source_indices=val_index_set,
                flag=flag,
                preferred_false=True,
                rng=rng,
            )
            if move_to_train is not None:
                val_index_set.remove(move_to_train)
                val_index_set.add(move_to_val)

        val_pos = [i for i in positives if i in val_index_set]
        train_pos = [i for i in positives if i not in val_index_set]
        if not train_pos and len(val_pos) > 1:
            move_to_train = rng.choice(val_pos)
            move_to_val = choose_swap_candidate(
                records=records,
                source_indices=all_indices - val_index_set,
                flag=flag,
                preferred_false=True,
                rng=rng,
            )
            if move_to_val is not None:
                val_index_set.add(move_to_val)
                val_index_set.remove(move_to_train)


def choose_swap_candidate(
    records: list[ManifestRecord],
    source_indices: set[int],
    flag: str,
    preferred_false: bool,
    rng: random.Random,
) -> int | None:
    source = list(source_indices)
    if not source:
        return None
    preferred = [i for i in source if bool(getattr(records[i], flag)) != preferred_false]
    if preferred:
        return rng.choice(preferred)
    return rng.choice(source)


def compute_binary_pos_weights(records: list[ManifestRecord]) -> dict[str, float]:
    total = len(records)

    def weight_for(flag: str) -> float:
        positives = count_positive(records, flag)
        negatives = total - positives
        if positives <= 0:
            return 1.0
        return max(1.0, negatives / positives)

    return {
        "is_variable_weight": weight_for("is_variable_weight"),
        "is_ambiguous": weight_for("is_ambiguous"),
        "is_unparsable": weight_for("is_unparsable"),
        "upc_present": weight_for("upc_present"),
    }


def write_manifest(path: Path, records: list[ManifestRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(
            {
                "image_filename": record.image_filename,
                "price": record.price,
                "net_quantity": record.net_quantity,
                "pack_count": record.pack_count,
                "quantity_unit": record.quantity_unit,
                "is_variable_weight": record.is_variable_weight,
                "is_ambiguous": record.is_ambiguous,
                "is_unparsable": record.is_unparsable,
                "upc_present": record.upc_present,
            },
            sort_keys=True,
        )
        for record in records
    ]
    path.write_text("\n".join(lines) + ("\n" if lines else ""))


def read_manifest(path: Path) -> list[ManifestRecord]:
    if not path.exists():
        return []
    records: list[ManifestRecord] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        records.append(
            ManifestRecord(
                image_filename=str(payload["image_filename"]),
                price=payload.get("price"),
                net_quantity=payload.get("net_quantity"),
                pack_count=payload.get("pack_count"),
                quantity_unit=payload.get("quantity_unit"),
                is_variable_weight=bool(payload.get("is_variable_weight", False)),
                is_ambiguous=bool(payload.get("is_ambiguous", False)),
                is_unparsable=bool(payload.get("is_unparsable", False)),
                upc_present=bool(payload.get("upc_present", False)),
            )
        )
    return records


def write_training_artifacts(
    output_dir: Path,
    config: AppConfig,
    history: list[dict[str, float]],
) -> None:
    metadata = {
        "experiment_name": config.experiment_name,
        "units": UNITS,
        "history": history,
    }
    (output_dir / "training_metrics.json").write_text(json.dumps(metadata, indent=2, sort_keys=True))


def print_final_summary(history: list[dict[str, float]]) -> None:
    if not history:
        return
    best = min(history, key=lambda row: row["val_loss"])
    last = history[-1]
    print("Final Validation Summary")
    print(
        f"  best_epoch={int(best['epoch'])} "
        f"best_val_loss={best['val_loss']:.4f} "
        f"best_unit_acc={best['val_unit_accuracy']:.3f}"
    )
    print(
        "  best_regression "
        f"price_mae={best['val_price_mae']:.3f} price_rmse={best['val_price_rmse']:.3f} "
        f"net_mae={best['val_net_quantity_mae']:.3f} net_rmse={best['val_net_quantity_rmse']:.3f} "
        f"pack_mae={best['val_pack_count_mae']:.3f} pack_rmse={best['val_pack_count_rmse']:.3f}"
    )
    print(
        "  best_binary "
        f"var_wt_f1={best['val_variable_weight_f1']:.3f} "
        f"ambiguous_f1={best['val_ambiguous_f1']:.3f} "
        f"unparsable_f1={best['val_unparsable_f1']:.3f}"
    )
    print(
        f"  final_epoch={int(last['epoch'])} "
        f"final_val_loss={last['val_loss']:.4f} "
        f"final_unit_acc={last['val_unit_accuracy']:.3f} "
        f"final_price_mae={last['val_price_mae']:.3f}"
    )


def save_checkpoint(
    path: Path,
    model: nn.Module,
    optimizer: AdamW,
    scheduler: CosineAnnealingLR,
    epoch: int,
    config: AppConfig,
    val_metrics: dict[str, float],
    trainer_type: str = "custom",
    alias_paths: list[Path] | None = None,
) -> None:
    checkpoint = {
        "epoch": epoch,
        "trainer_type": trainer_type,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict(),
        "config": config.model_dump(mode="json"),
        "units": UNITS,
        "val_metrics": val_metrics,
    }
    write_checkpoint_atomically(path, checkpoint)
    for alias_path in alias_paths or []:
        write_checkpoint_atomically(alias_path, checkpoint)


def write_checkpoint_atomically(path: Path, checkpoint: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent,
        prefix=f"{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
    try:
        torch.save(checkpoint, temp_path)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def resolve_device(requested: str) -> torch.device:
    if requested.startswith("cuda") and not torch.cuda.is_available():
        print("Requested CUDA but it is unavailable; falling back to CPU.")
        return torch.device("cpu")
    return torch.device(requested)


def resolve_num_workers(requested: int) -> int:
    workers = max(0, int(requested))
    if workers == 0:
        return 0
    try:
        lock = mp.get_context("spawn").Lock()
        lock.acquire()
        lock.release()
        return workers
    except Exception:
        print("Multiprocessing workers unavailable in this environment; using num_workers=0.")
        return 0


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


if __name__ == "__main__":
    main()
