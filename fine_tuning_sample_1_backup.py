import torch
import logging
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
from trl import SFTTrainer
import huggingface_hub

# 로깅 설정 초기화
logging.basicConfig(filename='training_log.log', level=logging.INFO)

# Hugging Face Hub 로그인 - 사용자 인터렉션 필요 확인
huggingface_hub.login()

# 모델 기본 설정
base_model = "meta-llama/Meta-Llama-3-8B-Instruct"
model_dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.get_device_capability(0)[0] >= 8 else torch.float16

# 모델과 토큰화기 로드
quant_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=model_dtype, bnb_4bit_use_double_quant=False)
model = AutoModelForCausalLM.from_pretrained(base_model, quantization_config=quant_config)
model.config.use_cache = False

tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

# 데이터셋 로드 및 토큰화 함수 정의
dataset = load_dataset("maywell/korean_textbooks")
train_dataset = dataset["train"]  # 훈련 데이터셋 지정

# 데이터 전처리 및 QA 데이터셋 변환
def prepare_qa_data(examples):
    questions = ["교과서에서 다루는 주요 주제는 무엇입니까?"] * len(examples["text"])
    answers = [{"text": ["교육"], "answer_start": [examples["text"][i].find("교육")]} for i in range(len(examples["text"]))]
    return {"question": questions, "context": examples["text"], "answers": answers}

qa_dataset = train_dataset.map(prepare_qa_data, batched=True, remove_columns=train_dataset.column_names)

# 토큰화 및 데이터 정렬
def tokenize_and_align_labels(examples):
    tokenized_inputs = tokenizer([examples["question"], examples["context"]], truncation=True, padding="max_length", max_length=512, return_tensors="pt")
    start_positions = []
    end_positions = []

    for i, (start, text) in enumerate(zip(examples["answers"]["answer_start"], examples["answers"]["text"])):
        start_positions.append(tokenized_inputs.char_to_token(i, start[0]))
        end_positions.append(tokenized_inputs.char_to_token(i, start[0] + len(text[0]) - 1))

    tokenized_inputs.update({"start_positions": start_positions, "end_positions": end_positions})
    return tokenized_inputs

tokenized_datasets = qa_dataset.map(tokenize_and_align_labels, batched=True)

# 훈련 설정
training_params = TrainingArguments(
    output_dir="./results", num_train_epochs=10, per_device_train_batch_size=4, gradient_accumulation_steps=1,
    optim="adamw", save_steps=25, logging_steps=25, learning_rate=2e-4, weight_decay=0.001,
    fp16=model_dtype==torch.float16, bf16=model_dtype==torch.bfloat16, max_grad_norm=0.3, warmup_ratio=0.03, group_by_length=True, lr_scheduler_type="constant",
    report_to="tensorboard"
)

# 훈련 진행
trainer = SFTTrainer(
    model=model, train_dataset=train_dataset, tokenizer=tokenizer, args=training_params, packing=False
)
trainer.train()
train_result = trainer.evaluate(tokenized_datasets["train"])
eval_result = trainer.evaluate(tokenized_datasets["validation"])

# 결과 로깅
logging.info(f"Training completed. Train Loss: {train_result['eval_loss']}")
logging.info(f"Evaluation completed. Validation Loss: {eval_result['eval_loss']}")

# 모델 저장
trainer.save_model("Llama-3-8B-Instruct-ko")