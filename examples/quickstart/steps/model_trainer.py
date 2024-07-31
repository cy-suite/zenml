# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2024. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from typing import Tuple

import torch
from datasets import Dataset
from transformers import (
    T5Tokenizer,
    T5ForConditionalGeneration,
    Trainer,
    TrainingArguments,
)
from typing_extensions import Annotated

from materializers import T5Materializer
from zenml import step
from zenml.logger import get_logger
from zenml.utils.enum_utils import StrEnum

logger = get_logger(__name__)


class T5_Model(StrEnum):
    """All possible types a `StackComponent` can have."""

    SMALL = "t5-small"
    LARGE = "t5-large"

@step(output_materializers=T5Materializer)
def train_model(
    tokenized_dataset: Dataset,
    model_type: T5_Model
) -> Tuple[Annotated[T5ForConditionalGeneration, "model"], Annotated[T5Tokenizer, "tokenizer"]]:
    """Train the model and return the path to the saved model."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = T5ForConditionalGeneration.from_pretrained(model_type)
    model.gradient_checkpointing_enable()  # Enable gradient checkpointing
    model = model.to(device)

    tokenizer = T5Tokenizer.from_pretrained(model_type)

    training_args = TrainingArguments(
        output_dir="./results",
        num_train_epochs=3,
        per_device_train_batch_size=1,  # Reduced batch size for larger model
        gradient_accumulation_steps=16,  # Increased gradient accumulation
        logging_dir="./logs",
        logging_steps=10,
        save_steps=50,
        fp16=True,  # Mixed precision training
        warmup_steps=500,
        learning_rate=3e-5,
        max_grad_norm=0.5,  # Gradient clipping
        dataloader_num_workers=4,  # Adjust based on your system
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
    )

    trainer.train()

    # Basic check
    test_input = tokenizer(
        "Translate Old English to Modern English: Hark, what light through yonder window breaks?",
        return_tensors="pt",
    ).to(device)
    with torch.no_grad():
        test_output = model.generate(**test_input)
    print(
        "Test translation:", tokenizer.decode(test_output[0], skip_special_tokens=True)
    )

    print("Model training completed and saved.")
    return trainer.model, tokenizer
