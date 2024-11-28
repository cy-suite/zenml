from __future__ import annotations

from typing import Annotated

import bentoml
import numpy as np
import torch
from bentoml.validators import DType, Shape
from constants import MODEL_NAME, SERVICE_NAME
from PIL.Image import Image as PILImage


def to_numpy(tensor):
    return tensor.detach().cpu().numpy()


@bentoml.service(
    name=SERVICE_NAME,
)
class MNISTService:
    def __init__(self):
        # load model
        self.model = bentoml.pytorch.load_model(MODEL_NAME)
        self.model.eval()

    @bentoml.api()
    def predict_ndarray(
        self, inp: Annotated[np.ndarray, DType("float32"), Shape((28, 28))]
    ) -> np.ndarray:
        # We are using greyscale image and our PyTorch model expect one
        # extra channel dimension. Then we will also add one batch
        # dimension

        inp = np.expand_dims(inp, (0, 1))
        output_tensor = self.model(torch.tensor(inp))
        return to_numpy(output_tensor)

    @bentoml.api()
    def predict_image(self, f: PILImage) -> np.ndarray:
        assert isinstance(f, PILImage)
        arr = np.array(f) / 255.0
        assert arr.shape == (28, 28)

        # We are using greyscale image and our PyTorch model expect one
        # extra channel dimension. Then we will also add one batch
        # dimension
        arr = np.expand_dims(arr, (0, 1)).astype("float32")
        output_tensor = self.model(torch.tensor(arr))
        return to_numpy(output_tensor)
