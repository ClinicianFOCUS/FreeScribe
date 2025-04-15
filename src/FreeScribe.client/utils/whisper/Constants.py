"""
This software is released under the AGPL-3.0 license
Copyright (c) 2023-2025 Braedon Hendy

Further updates and packaging added in 2024-2025 through the ClinicianFOCUS initiative,
a collaboration with Dr. Braedon Hendy and Conestoga College Institute of Applied
Learning and Technology as part of the CNERG+ applied research project,
Unburdening Primary Healthcare: An Open-Source AI Clinician Partner Platform.
Prof. Michael Yingbull (PI), Dr. Braedon Hendy (Partner),
and Research Students (Software Developers) -
Alex Simko, Pemba Sherpa, Naitik Patel, Yogesh Kumar and Xun Zhong.
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import utils.system
import platform


@dataclass
class ModelInfo:
    """
    Dataclass to store information about a whisper models
    """
    label: str
    windows_value: str
    macos_value: str


class WhisperModels(Enum):
    """
    Enum to represent the available whisper models
    """

    TINY = ModelInfo(label="Tiny", windows_value="tiny", macos_value="openai/whisper-tiny")
    TINY_EN = ModelInfo(label="Tiny (English Only)", windows_value="tiny.en", macos_value="openai/whisper-tiny.en")
    SMALL = ModelInfo(label="Small", windows_value="small", macos_value="openai/whisper-small")
    SMALL_EN = ModelInfo(label="Small (English Only)", windows_value="small.en", macos_value="openai/whisper-small.en")
    MEDIUM = ModelInfo(label="Medium", windows_value="medium", macos_value="openai/whisper-medium")
    MEDIUM_EN = ModelInfo(
        label="Medium (English Only)",
        windows_value="medium.en",
        macos_value="openai/whisper-medium.en")
    BASE = ModelInfo(label="Base", windows_value="base", macos_value="openai/whisper-base")
    BASE_EN = ModelInfo(label="Base (English Only)", windows_value="base.en", macos_value="openai/whisper-base.en")
    LARGE = ModelInfo(label="Large", windows_value="large", macos_value="openai/whisper-large")
    TURBO = ModelInfo(label="Turbo", windows_value="turbo", macos_value="openai/whisper-large-v3-turbo")

    @property
    def label(self) -> str:
        """
        Get the label of the model
        """
        return self.value.label

    @property
    def windows_value(self) -> str:
        """
        Get the value of the model for Windows
        """
        return self.value.windows_value

    @property
    def macos_value(self) -> str:
        """
        Get the value of the model for MacOS
        """
        return self.value.macos_value

    @property
    def linux_value(self) -> str:
        """
        Get the value of the model for Linux
        """
        # Linux will be sharing the values that windows use
        return self.value.windows_value

    def get_platform_value(self) -> str:
        """Get the appropriate value for the specified platform"""
        if utils.system.is_windows():
            return self.windows_value
        elif utils.system.is_macos():
            return self.macos_value
        elif utils.system.is_linux():
            return self.linux_value
        else:
            raise ValueError(f"Unsupported platform: {platform.system()}")

    @classmethod
    def get_all_labels(cls) -> list[str]:
        """
        Get a list of all the labels of the models
        """
        return [model.label for model in cls]

    @classmethod
    def find_by_label(cls, label: str) -> Optional["WhisperModels"]:
        """
        Find a model by its label
        """

        return next((model for model in cls if model.label == label), None)

    def __str__(self) -> str:
        """
        Get the string representation of the model
        """
        return self.label
