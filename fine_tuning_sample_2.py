import os
import torch
from datasets import load_dataset

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    pipeline,
    logging,
)
from peft import LoraConfig
from trl import SFTTrainer

import huggingface_hub
huggingface_hub.login()
# huggingface 로그인

### 모델 설정 (본인 hugging dataset 폴더 참고 ★)
# Hugging Face Basic Model 한국어 모델
base_model = "beomi/Llama-3-Open-Ko-8B"

# Custom Dataset ★ 본인이 hugging face 내 저장한 모델경로를 설정해야함 ★
hkcode_dataset = "hyokwan/hkcode_korea"

new_model = "Llama-hkcode-Ko-3-8B"

dataset = load_dataset(hkcode_dataset, split="train")

# 데이터 확인
print( dataset[28] )


### 4비트 양자화 QLoRa 파인튜닝(효율성) * 파라미터 고정 시키고 추가데이터만 튜닝
if torch.cuda.get_device_capability()[0] >= 8:
    !pip install -qqq flash-attn
    attn_implementation = "flash_attention_2"
    torch_dtype = torch.bfloat16
else:
    attn_implementation = "eager"
    torch_dtype = torch.float16

# QLoRA config
quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch_dtype,
    bnb_4bit_use_double_quant=False,
)

### 라마2모델 불러오기
model = AutoModelForCausalLM.from_pretrained(
    base_model,
    quantization_config=quant_config,
    device_map={"": 0}
    # device_map="auto"
)
model.config.use_cache = False
model.config.pretraining_tp = 1

### 토크나이저 불러오기 (Hugginface에서 토크나이저를 로드하고 padding_side를 "right"로 설정하여 fp16과 관련된 문제해결)
tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

### PEFT 파라미터 (Parameter-Efficient Fine-Tuning (PEFT)은 모델 파라미터의 작은 하위 집합만 업데이트)
# https://huggingface.co/docs/peft/conceptual_guides/lora
peft_params = LoraConfig(
    lora_alpha=16,
    lora_dropout=0.1,
    r=64,
    bias="none",
    task_type="CAUSAL_LM",
)

### Training parameters
training_params = TrainingArguments(
    output_dir="./results",
    num_train_epochs=10,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=1,
    optim="paged_adamw_32bit",
    save_steps=25,
    logging_steps=25,
    learning_rate=2e-4,
    weight_decay=0.001,
    fp16=False,
    bf16=False,
    max_grad_norm=0.3,
    max_steps=-1,
    warmup_ratio=0.03,
    group_by_length=True,
    lr_scheduler_type="constant",
    report_to="tensorboard"
)

### model 파인튜닝
trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    peft_config=peft_params,
    dataset_text_field="text",
    max_seq_length=None,
    tokenizer=tokenizer,
    args=training_params,
    packing=False,
)

trainer.train()

#Step	Training Loss
#25	2.274800
#50	0.862200
#75	0.403000

logging.set_verbosity(logging.CRITICAL)

prompt = "스마트금융과는 어디에 위치하나요?"
pipe = pipeline(task="text-generation", model=model, tokenizer=tokenizer, max_length=200)
result = pipe(f"<s>[INST] {prompt} [/INST]")
print(result[0]['generated_text'])

trainer.save_model(new_model)