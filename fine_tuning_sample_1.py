import torch
import logging
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoModelForTokenClassification, BertForTokenClassification, BertTokenizer, TrainingArguments, pipeline, Trainer
from trl import SFTTrainer
import huggingface_hub

# 로깅 설정 초기화 - 로그 파일을 시작할 때 비우기
logging.basicConfig(filename='training_log.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filemode='w')

# Hugging Face Hub 로그인 - 사용자 인터렉션 필요 확인
huggingface_hub.login()

# 모델 기본 설정
base_model = "meta-llama/Meta-Llama-3-8B-Instruct"
ner_model_name = "beomi/KcELECTRA-base-v2022"  # KcELECTRA 모델

# 로깅: 모델 로드 시작
logging.info("Loading models and tokenizers")

# 메인 모델과 토큰화기 로드
main_model = AutoModelForCausalLM.from_pretrained(base_model, use_auth_token=False)
main_model.config.use_cache = False
main_tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
main_tokenizer.pad_token = main_tokenizer.eos_token
main_tokenizer.padding_side = "right"

# KcELECTRA NER 모델 로드
ner_model = BertForTokenClassification.from_pretrained(ner_model_name)
ner_tokenizer = BertTokenizer.from_pretrained(ner_model_name)

# NER 파이프라인 설정
ner_pipeline = pipeline("ner", model=ner_model, tokenizer=ner_tokenizer, aggregation_strategy="simple")

# 로깅: 데이터셋 로드
logging.info("Loading dataset")
dataset = load_dataset("maywell/korean_textbooks", "claude_evol")

# 데이터 전처리 및 QA 데이터셋 변환
def prepare_qa_data(examples):
    logging.info("Preparing QA data with NER")
    questions = []
    answers = []
    contexts = []

    for i, text in enumerate(examples["text"]):
        ner_results = ner_pipeline(text)
        found = False
        for ent in ner_results:
            if ent['entity_group'] in ['PER', 'ORG', 'LOC']:
                question = f"What is mentioned about {ent['word']} in the text?"
                questions.append(question)
                answer_start = text.find(ent['word'])
                if answer_start != -1:
                    answers.append({"text": [ent['word']], "answer_start": [answer_start]})
                    contexts.append(text)
                    found = True
                    logging.info(f"Entity '{ent['word']}' found in text {i}: position {answer_start}")

        if not found:
            questions.append("What is the main topic of the text?")
            answers.append({"text": ["No specific topic"], "answer_start": [0]})
            contexts.append(text)
            logging.warning(f"No significant entities found in text {i}")

    return {"question": questions, "context": contexts, "answers": answers}

qa_dataset = dataset["train"].map(prepare_qa_data, batched=True)

# 토큰화 및 데이터 정렬
def tokenize_and_align_labels(examples):
    tokenized_inputs = main_tokenizer(examples["context"], examples["question"], truncation=True, padding="max_length", max_length=512)
    return tokenized_inputs

tokenized_datasets = qa_dataset.map(tokenize_and_align_labels, batched=True)

# 훈련 설정
training_params = TrainingArguments(
    output_dir="./results", num_train_epochs=10, per_device_train_batch_size=4, gradient_accumulation_steps=1,
    optim="adamw", save_steps=25, logging_steps=25, learning_rate=2e-4, weight_decay=0.001,
    max_grad_norm=0.3, warmup_ratio=0.03, group_by_length=True, lr_scheduler_type="constant",
    report_to="tensorboard"
)

# 훈련 진행
logging.info("Starting training")
trainer = SFTTrainer(
    model=main_model, train_dataset=tokenized_datasets["train"], tokenizer=main_tokenizer, args=training_params, packing=False
)
trainer.train()
train_result = trainer.evaluate(tokenized_datasets["train"])
eval_result = trainer.evaluate(tokenized_datasets["validation"])

# 결과 로깅
logging.info(f"Training completed. Train Loss: {train_result['eval_loss']}")
logging.info(f"Evaluation completed. Validation Loss: {eval_result['eval_loss']}")

# 모델 저장
trainer.save_model("Llama-3-8B-Instruct-ko")

# Hugging Face Hub에 모델 업로드
class MyTrainer(Trainer):
    def push_to_hub(self):
        # 모델 저장
        self.save_model()

        # Hugging Face Hub에 업로드
        self.model.push_to_hub("MyLlama-3-8B-Instruct-ko")
        self.tokenizer.push_to_hub("MyLlama-3-8B-Instruct-ko")

# 트레이너 인스턴스 생성
my_trainer = MyTrainer(
    model=main_model, 
    args=training_params, 
    train_dataset=tokenized_datasets["train"], 
    eval_dataset=tokenized_datasets["validation"], 
    tokenizer=main_tokenizer
)

# Hub에 모델 업로드
my_trainer.push_to_hub()