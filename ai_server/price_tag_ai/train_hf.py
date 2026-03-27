from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from torch import nn
from transformers import Trainer, TrainingArguments, ViTConfig, ViTModel

from price_tag_ai.config import AppConfig, load_config
from price_tag_ai.train import (
    PriceTagModel,
    PriceTagTorchDataset,
    binary_stats,
    build_optimizer,
    build_run_timestamp,
    build_scheduler,
    compute_batch_metrics,
    compute_binary_pos_weights,
    configure_wandb_env,
    finish_wandb_run,
    generate_splits,
    parse_args,
    print_final_summary,
    read_manifest,
    resolve_num_workers,
    save_checkpoint,
    set_seed,
    write_training_artifacts,
)


LABEL_NAMES = [
    "price",
    "price_mask",
    "net_quantity",
    "net_quantity_mask",
    "pack_count",
    "pack_count_mask",
    "quantity_unit_index",
    "quantity_unit_mask",
    "is_variable_weight",
    "is_ambiguous",
    "is_unparsable",
    "upc_present",
]


class HFPriceTagModel(nn.Module):
    """Legacy HF checkpoint class retained for backward-compatible checkpoint loading."""

    def __init__(
        self,
        config: AppConfig,
        binary_pos_weights: dict[str, float],
        load_pretrained_encoder: bool = True,
    ):
        super().__init__()
        self.app_config = config
        self.binary_pos_weights = binary_pos_weights

        if config.model.pretrained and load_pretrained_encoder:
            self.encoder = ViTModel.from_pretrained(config.model.hf_model_name)
            hidden_size = int(self.encoder.config.hidden_size)
        else:
            vit_config = ViTConfig(
                image_size=config.model.image_size,
                num_channels=3,
                hidden_dropout_prob=config.model.dropout,
                attention_probs_dropout_prob=config.model.dropout,
            )
            self.encoder = ViTModel(vit_config)
            hidden_size = int(vit_config.hidden_size)

        self.dropout = nn.Dropout(config.model.dropout)
        self.head_price = nn.Linear(hidden_size, 1)
        self.head_net_quantity = nn.Linear(hidden_size, 1)
        self.head_pack_count = nn.Linear(hidden_size, 1)
        self.head_unit = nn.Linear(hidden_size, 12)
        self.head_variable_weight = nn.Linear(hidden_size, 1)
        self.head_ambiguous = nn.Linear(hidden_size, 1)
        self.head_unparsable = nn.Linear(hidden_size, 1)
        self.head_upc_present = nn.Linear(hidden_size, 1)

    def forward(self, pixel_values: torch.Tensor, **_: Any) -> dict[str, torch.Tensor]:
        encoded = self.encoder(pixel_values=pixel_values)
        features = self.dropout(encoded.last_hidden_state[:, 0])
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


class PriceTagTrainer(Trainer):
    def __init__(
        self,
        *args: Any,
        app_config: AppConfig,
        binary_pos_weights: dict[str, float],
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.app_config = app_config
        self.binary_pos_weights = binary_pos_weights

    def create_optimizer_and_scheduler(self, num_training_steps: int) -> None:
        if self.optimizer is None:
            self.optimizer = build_optimizer(self.model, self.app_config)
        if self.lr_scheduler is None:
            self.lr_scheduler = build_scheduler(self.optimizer, self.app_config)

    def compute_loss(
        self,
        model: nn.Module,
        inputs: dict[str, torch.Tensor],
        return_outputs: bool = False,
        **_: Any,
    ):
        outputs = model(inputs["images"])
        loss = compute_multitask_loss(
            outputs=outputs,
            price=inputs["price"],
            price_mask=inputs["price_mask"],
            net_quantity=inputs["net_quantity"],
            net_quantity_mask=inputs["net_quantity_mask"],
            pack_count=inputs["pack_count"],
            pack_count_mask=inputs["pack_count_mask"],
            quantity_unit_index=inputs["quantity_unit_index"],
            is_variable_weight=inputs["is_variable_weight"],
            is_ambiguous=inputs["is_ambiguous"],
            is_unparsable=inputs["is_unparsable"],
            upc_present=inputs["upc_present"],
            binary_pos_weights=self.binary_pos_weights,
            device=inputs["images"].device,
        )
        return (loss, outputs) if return_outputs else loss


def parse_cli_args() -> argparse.Namespace:
    return parse_args()


def main() -> None:
    args = parse_cli_args()
    config = load_config(*args.configs)
    run_training(config)


def run_training(config: AppConfig) -> None:
    set_seed(config.train.seed)

    output_dir = Path(config.train.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_timestamp = build_run_timestamp()
    configure_wandb_env(config, run_timestamp)

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
    binary_pos_weights = compute_binary_pos_weights(train_records)
    model = PriceTagModel(
        backbone=config.model.backbone,
        dropout=config.model.dropout,
        pretrained=config.model.pretrained,
    )

    best_checkpoint_path = output_dir / f"best-{run_timestamp}.pt"

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=config.train.batch_size,
        per_device_eval_batch_size=config.train.batch_size,
        num_train_epochs=config.train.epochs,
        learning_rate=config.optimizer.lr,
        weight_decay=config.optimizer.weight_decay,
        dataloader_num_workers=current_num_workers,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        remove_unused_columns=False,
        report_to=["wandb"] if config.wandb.enabled else [],
        run_name=run_timestamp,
        seed=config.train.seed,
        data_seed=config.train.seed,
        label_names=LABEL_NAMES,
        save_total_limit=2,
    )

    trainer = PriceTagTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=price_tag_data_collator,
        compute_metrics=compute_eval_metrics,
        app_config=config,
        binary_pos_weights=binary_pos_weights,
    )

    print(f"Experiment: {config.experiment_name}")
    print(f"Trainer backbone: {config.model.backbone}")
    print(f"Pretrained: {config.model.pretrained}")
    print(f"Train samples: {len(train_dataset)}")
    print(f"Val samples: {len(val_dataset)}")
    print(f"DataLoader workers: {current_num_workers}")
    print(f"Output dir: {output_dir}")
    print(
        "Augmentation mode: on-the-fly stochastic sampling "
        "(dataset size stays constant; train samples are regenerated per access)"
    )
    print(
        "Binary prevalence (train positives / total): "
        f"var={count_positive_metric(train_records, 'is_variable_weight')}/{len(train_records)}, "
        f"amb={count_positive_metric(train_records, 'is_ambiguous')}/{len(train_records)}, "
        f"unpars={count_positive_metric(train_records, 'is_unparsable')}/{len(train_records)}, "
        f"upc={count_positive_metric(train_records, 'upc_present')}/{len(train_records)}"
    )

    try:
        trainer.train()
        eval_metrics = trainer.evaluate()

        history = build_history_from_log_history(trainer.state.log_history)
        print_final_summary(history)
        write_training_artifacts(output_dir, config, history)

        if trainer.optimizer is not None and trainer.lr_scheduler is not None:
            save_checkpoint(
                best_checkpoint_path,
                trainer.model,
                trainer.optimizer,
                trainer.lr_scheduler,
                int(trainer.state.global_step),
                config,
                normalize_eval_metrics(eval_metrics),
                trainer_type="custom",
                alias_paths=[output_dir / "best.pt", output_dir / "best_hf.pt"],
            )

        print("Training complete.")
    finally:
        if config.wandb.enabled:
            finish_wandb_run(config)


def compute_multitask_loss(
    outputs: dict[str, torch.Tensor],
    price: torch.Tensor,
    price_mask: torch.Tensor | None,
    net_quantity: torch.Tensor | None,
    net_quantity_mask: torch.Tensor | None,
    pack_count: torch.Tensor | None,
    pack_count_mask: torch.Tensor | None,
    quantity_unit_index: torch.Tensor | None,
    is_variable_weight: torch.Tensor | None,
    is_ambiguous: torch.Tensor | None,
    is_unparsable: torch.Tensor | None,
    upc_present: torch.Tensor | None,
    binary_pos_weights: dict[str, float],
    device: torch.device,
) -> torch.Tensor:
    losses: list[torch.Tensor] = []
    losses.append(masked_mse(outputs["price"], price, price_mask))
    losses.append(masked_mse(outputs["net_quantity"], net_quantity, net_quantity_mask))
    losses.append(masked_mse(outputs["pack_count"], pack_count, pack_count_mask))
    losses.append(
        F.cross_entropy(
            outputs["unit_logits"],
            quantity_unit_index,
            ignore_index=-100,
        )
    )
    losses.append(
        F.binary_cross_entropy_with_logits(
            outputs["variable_weight_logit"],
            is_variable_weight,
            pos_weight=torch.tensor(binary_pos_weights["is_variable_weight"], device=device, dtype=torch.float32),
        )
    )
    losses.append(
        F.binary_cross_entropy_with_logits(
            outputs["ambiguous_logit"],
            is_ambiguous,
            pos_weight=torch.tensor(binary_pos_weights["is_ambiguous"], device=device, dtype=torch.float32),
        )
    )
    losses.append(
        F.binary_cross_entropy_with_logits(
            outputs["unparsable_logit"],
            is_unparsable,
            pos_weight=torch.tensor(binary_pos_weights["is_unparsable"], device=device, dtype=torch.float32),
        )
    )
    losses.append(
        F.binary_cross_entropy_with_logits(
            outputs["upc_present_logit"],
            upc_present,
            pos_weight=torch.tensor(binary_pos_weights["upc_present"], device=device, dtype=torch.float32),
        )
    )
    return sum(losses)


def masked_mse(
    pred: torch.Tensor | None,
    target: torch.Tensor | None,
    mask: torch.Tensor | None,
) -> torch.Tensor:
    if pred is None or target is None or mask is None:
        raise ValueError("Regression labels must be present for multitask loss")
    if mask.sum().item() == 0:
        return pred.new_tensor(0.0)
    return F.mse_loss(pred[mask], target[mask])


def price_tag_data_collator(features: list[dict[str, Any]]) -> dict[str, torch.Tensor]:
    batch: dict[str, torch.Tensor] = {}
    batch["images"] = torch.stack([feature["image"] for feature in features])
    for key in LABEL_NAMES:
        batch[key] = torch.stack([feature[key] for feature in features])
    return batch


def compute_eval_metrics(eval_prediction: Any) -> dict[str, float]:
    if hasattr(eval_prediction, "predictions"):
        predictions = eval_prediction.predictions
        labels = eval_prediction.label_ids
    else:
        predictions, labels = eval_prediction
    (
        price,
        net_quantity,
        pack_count,
        unit_logits,
        variable_weight_logit,
        ambiguous_logit,
        unparsable_logit,
        upc_present_logit,
    ) = predictions
    (
        label_price,
        label_price_mask,
        label_net_quantity,
        label_net_quantity_mask,
        label_pack_count,
        label_pack_count_mask,
        label_quantity_unit_index,
        label_quantity_unit_mask,
        label_is_variable_weight,
        label_is_ambiguous,
        label_is_unparsable,
        label_upc_present,
    ) = labels

    batch = {
        "price": torch.tensor(label_price),
        "price_mask": torch.tensor(label_price_mask, dtype=torch.bool),
        "net_quantity": torch.tensor(label_net_quantity),
        "net_quantity_mask": torch.tensor(label_net_quantity_mask, dtype=torch.bool),
        "pack_count": torch.tensor(label_pack_count),
        "pack_count_mask": torch.tensor(label_pack_count_mask, dtype=torch.bool),
        "quantity_unit_index": torch.tensor(label_quantity_unit_index, dtype=torch.long),
        "quantity_unit_mask": torch.tensor(label_quantity_unit_mask, dtype=torch.bool),
        "is_variable_weight": torch.tensor(label_is_variable_weight),
        "is_ambiguous": torch.tensor(label_is_ambiguous),
        "is_unparsable": torch.tensor(label_is_unparsable),
        "upc_present": torch.tensor(label_upc_present),
    }
    outputs = {
        "price": torch.tensor(price),
        "net_quantity": torch.tensor(net_quantity),
        "pack_count": torch.tensor(pack_count),
        "unit_logits": torch.tensor(unit_logits),
        "variable_weight_logit": torch.tensor(variable_weight_logit),
        "ambiguous_logit": torch.tensor(ambiguous_logit),
        "unparsable_logit": torch.tensor(unparsable_logit),
        "upc_present_logit": torch.tensor(upc_present_logit),
    }
    metrics = compute_batch_metrics(batch, outputs, torch.device("cpu"))
    variable_stats = binary_stats(
        metrics["variable_tp"],
        metrics["variable_fp"],
        metrics["variable_fn"],
        metrics["variable_tn"],
    )
    ambiguous_stats = binary_stats(
        metrics["ambiguous_tp"],
        metrics["ambiguous_fp"],
        metrics["ambiguous_fn"],
        metrics["ambiguous_tn"],
    )
    unparsable_stats = binary_stats(
        metrics["unparsable_tp"],
        metrics["unparsable_fp"],
        metrics["unparsable_fn"],
        metrics["unparsable_tn"],
    )
    upc_stats = binary_stats(
        metrics["upc_tp"],
        metrics["upc_fp"],
        metrics["upc_fn"],
        metrics["upc_tn"],
    )

    return {
        "price_mae": metrics["price_abs_sum"] / max(1.0, metrics["price_count"]),
        "price_rmse": (metrics["price_sq_sum"] / max(1.0, metrics["price_count"])) ** 0.5,
        "net_quantity_mae": metrics["net_abs_sum"] / max(1.0, metrics["net_count"]),
        "net_quantity_rmse": (metrics["net_sq_sum"] / max(1.0, metrics["net_count"])) ** 0.5,
        "pack_count_mae": metrics["pack_abs_sum"] / max(1.0, metrics["pack_count"]),
        "pack_count_rmse": (metrics["pack_sq_sum"] / max(1.0, metrics["pack_count"])) ** 0.5,
        "unit_accuracy": metrics["unit_correct"] / max(1.0, metrics["unit_total"]),
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


def build_history_from_log_history(log_history: list[dict[str, Any]]) -> list[dict[str, float]]:
    history: list[dict[str, float]] = []
    for row in log_history:
        if "eval_loss" not in row:
            continue
        history.append(
            {
                "epoch": float(row.get("epoch", len(history) + 1)),
                "train_loss": float(row.get("loss", float("nan"))),
                "val_loss": float(row["eval_loss"]),
                "val_price_mae": float(row.get("eval_price_mae", 0.0)),
                "val_price_rmse": float(row.get("eval_price_rmse", 0.0)),
                "val_net_quantity_mae": float(row.get("eval_net_quantity_mae", 0.0)),
                "val_net_quantity_rmse": float(row.get("eval_net_quantity_rmse", 0.0)),
                "val_pack_count_mae": float(row.get("eval_pack_count_mae", 0.0)),
                "val_pack_count_rmse": float(row.get("eval_pack_count_rmse", 0.0)),
                "val_unit_accuracy": float(row.get("eval_unit_accuracy", 0.0)),
                "val_variable_weight_accuracy": float(row.get("eval_variable_weight_accuracy", 0.0)),
                "val_variable_weight_precision": float(row.get("eval_variable_weight_precision", 0.0)),
                "val_variable_weight_recall": float(row.get("eval_variable_weight_recall", 0.0)),
                "val_variable_weight_f1": float(row.get("eval_variable_weight_f1", 0.0)),
                "val_ambiguous_accuracy": float(row.get("eval_ambiguous_accuracy", 0.0)),
                "val_ambiguous_precision": float(row.get("eval_ambiguous_precision", 0.0)),
                "val_ambiguous_recall": float(row.get("eval_ambiguous_recall", 0.0)),
                "val_ambiguous_f1": float(row.get("eval_ambiguous_f1", 0.0)),
                "val_unparsable_accuracy": float(row.get("eval_unparsable_accuracy", 0.0)),
                "val_unparsable_precision": float(row.get("eval_unparsable_precision", 0.0)),
                "val_unparsable_recall": float(row.get("eval_unparsable_recall", 0.0)),
                "val_unparsable_f1": float(row.get("eval_unparsable_f1", 0.0)),
                "val_upc_present_accuracy": float(row.get("eval_upc_present_accuracy", 0.0)),
                "val_upc_present_precision": float(row.get("eval_upc_present_precision", 0.0)),
                "val_upc_present_recall": float(row.get("eval_upc_present_recall", 0.0)),
                "val_upc_present_f1": float(row.get("eval_upc_present_f1", 0.0)),
            }
        )
    return history


def count_positive_metric(records: list[Any], flag: str) -> int:
    return sum(1 for record in records if bool(getattr(record, flag)))


def normalize_eval_metrics(metrics: dict[str, float]) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for key, value in metrics.items():
        if key.startswith("eval_"):
            normalized[key[5:]] = float(value)
        elif isinstance(value, (int, float)):
            normalized[key] = float(value)
    return normalized


if __name__ == "__main__":
    main()
