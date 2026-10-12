"""Architectures comparées. Chaque modèle prend (B, 3, H, W) et renvoie un logit (B,)."""

from __future__ import annotations

import torch
from torch import nn


class SimpleCNN(nn.Module):
    """Référence basse : 4 blocs convolutifs entraînés depuis zéro."""

    def __init__(self, in_channels: int = 3) -> None:
        super().__init__()
        chans = [in_channels, 16, 32, 64, 128]
        blocks: list[nn.Module] = []
        for cin, cout in zip(chans[:-1], chans[1:], strict=True):
            blocks += [
                nn.Conv2d(cin, cout, 3, padding=1, bias=False),
                nn.BatchNorm2d(cout),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(2),
            ]
        self.features = nn.Sequential(*blocks)
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.head = nn.Linear(chans[-1], 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = self.pool(self.features(x)).flatten(1)
        out: torch.Tensor = self.head(z).squeeze(1)
        return out


class _Wrapped(nn.Module):
    """Garantit une sortie (B,) quel que soit le backbone."""

    def __init__(self, backbone: nn.Module) -> None:
        super().__init__()
        self.backbone = backbone

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out: torch.Tensor = self.backbone(x).reshape(x.shape[0])
        return out


def build_model(name: str, pretrained: bool = True) -> nn.Module:
    if name == "simple_cnn":
        return SimpleCNN()
    if name == "resnet18":
        from torchvision.models import ResNet18_Weights, resnet18

        m = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1 if pretrained else None)
        m.fc = nn.Linear(m.fc.in_features, 1)
        return _Wrapped(m)
    if name == "densenet121":
        from torchvision.models import DenseNet121_Weights, densenet121

        d = densenet121(weights=DenseNet121_Weights.IMAGENET1K_V1 if pretrained else None)
        d.classifier = nn.Linear(d.classifier.in_features, 1)
        return _Wrapped(d)
    if name == "efficientnet_b0":
        import timm

        return _Wrapped(timm.create_model("efficientnet_b0", pretrained=pretrained, num_classes=1))
    raise ValueError(f"Modèle inconnu : {name}")
