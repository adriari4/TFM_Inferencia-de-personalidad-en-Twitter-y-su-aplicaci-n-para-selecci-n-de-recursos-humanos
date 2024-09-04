# -*- coding: utf-8 -*-
"""DistilBERT 83%.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1xTkPLbhOYoSue_p9e68jJa-Xy6CfqyD9
"""

!pip install imbalanced-learn

import torch
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
from torch.utils.data import DataLoader, Dataset
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import pandas as pd
from imblearn.over_sampling import RandomOverSampler
from sklearn.preprocessing import LabelEncoder
from google.colab import files
import io

# Subir archivos
uploaded = files.upload()
# 1. Cargar el dataset desde el archivo CSV
data = pd.read_csv('/mnt/data/Final_combinedMBIT_dataset.csv')

# Subir archivos
uploaded = files.upload()
# 1. Cargar el dataset desde el archivo CSV
data = pd.read_csv('/mnt/data/Final_combinedMBIT_dataset.csv')
# Cargar el archivo CSV
data = pd.read_csv('Final_combinedMBIT_dataset.csv')

# Mostrar los nombres de las columnas
print(data.columns)
# Eliminar filas con NaN en la columna 'TWEETS'
data = data.dropna(subset=['TWEETS'])

# Eliminar filas con NaN en la columna 'TWEETS'
data = data.dropna(subset=['TWEETS'])

# Codificar las etiquetas
X = data['TWEETS'].tolist()
y = data['PERSONALIDAD MBIT '].tolist()

label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

# Balancear el dataset utilizando sobremuestreo
oversampler = RandomOverSampler(random_state=42)
X_resampled, y_resampled = oversampler.fit_resample(pd.DataFrame(X), y_encoded)

# Convertir la columna de texto resampleada a lista
X_resampled = X_resampled[0].tolist()

# Dividir los datos en conjunto de entrenamiento y prueba
X_train, X_test, y_train, y_test = train_test_split(X_resampled, y_resampled, test_size=0.2, random_state=42)

# Crear un dataset personalizado para PyTorch
class TextDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = self.texts[idx]
        label = self.labels[idx]

        encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_len,
            truncation=True,  # Activar truncation
            padding='max_length',  # Cambiar a padding='max_length'
            return_token_type_ids=False,
            return_attention_mask=True,
            return_tensors='pt',
        )

        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

# Configuración de parámetros y carga de DistilBERT
BATCH_SIZE = 16
MAX_LEN = 128
EPOCHS = 10
LEARNING_RATE = 1e-5  # Reducir la tasa de aprendizaje
WEIGHT_DECAY = 1e-4  # Aumentar el weight decay

# Cargar el tokenizador y el modelo DistilBERT
tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')
model = DistilBertForSequenceClassification.from_pretrained('distilbert-base-uncased', num_labels=len(set(y_encoded)))
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# Crear DataLoaders
train_dataset = TextDataset(
    texts=X_train,
    labels=y_train,
    tokenizer=tokenizer,
    max_len=MAX_LEN
)

test_dataset = TextDataset(
    texts=X_test,
    labels=y_test,
    tokenizer=tokenizer,
    max_len=MAX_LEN
)

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

# Definir el optimizador con weight decay
optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)

# Función de entrenamiento
def train_epoch(model, data_loader, optimizer, device):
    model = model.train()
    total_loss = 0
    correct_predictions = 0

    for d in data_loader:
        input_ids = d["input_ids"].to(device)
        attention_mask = d["attention_mask"].to(device)
        labels = d["labels"].to(device)

        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels
        )

        loss = outputs.loss
        logits = outputs.logits

        _, preds = torch.max(logits, dim=1)
        correct_predictions += torch.sum(preds == labels)
        total_loss += loss.item()

        loss.backward()
        optimizer.step()
        optimizer.zero_grad()

    return correct_predictions.double() / len(data_loader.dataset), total_loss / len(data_loader)

# Función de evaluación
def eval_model(model, data_loader, device):
    model = model.eval()
    correct_predictions = 0
    total_loss = 0

    with torch.no_grad():
        for d in data_loader:
            input_ids = d["input_ids"].to(device)
            attention_mask = d["attention_mask"].to(device)
            labels = d["labels"].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )

            loss = outputs.loss
            logits = outputs.logits

            _, preds = torch.max(logits, dim=1)
            correct_predictions += torch.sum(preds == labels)
            total_loss += loss.item()

    return correct_predictions.double() / len(data_loader.dataset), total_loss / len(data_loader)

# Entrenamiento del modelo
for epoch in range(EPOCHS):
    print(f'Epoch {epoch + 1}/{EPOCHS}')
    print('-' * 10)

    train_acc, train_loss = train_epoch(model, train_loader, optimizer, device)
    print(f'Train loss {train_loss} accuracy {train_acc}')

    val_acc, val_loss = eval_model(model, test_loader, device)
    print(f'Validation loss {val_loss} accuracy {val_acc}')
    print()

# Evaluación final del modelo en el conjunto de prueba
y_pred = []
y_true = []

model.eval()
with torch.no_grad():
    for d in test_loader:
        input_ids = d['input_ids'].to(device)
        attention_mask = d['attention_mask'].to(device)
        labels = d['labels'].to(device)

        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        _, preds = torch.max(outputs.logits, dim=1)

        y_pred.extend(preds)
        y_true.extend(labels)

y_pred = torch.stack(y_pred).cpu()
y_true = torch.stack(y_true).cpu()

print(classification_report(y_true, y_pred))

from sklearn.metrics import confusion_matrix, f1_score
import seaborn as sns
import matplotlib.pyplot as plt

# Evaluación final del modelo en el conjunto de prueba
y_pred = []
y_true = []

model.eval()
with torch.no_grad():
    for d in test_loader:
        input_ids = d['input_ids'].to(device)
        attention_mask = d['attention_mask'].to(device)
        labels = d['labels'].to(device)

        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        _, preds = torch.max(outputs.logits, dim=1)

        y_pred.extend(preds)
        y_true.extend(labels)

y_pred = torch.stack(y_pred).cpu()
y_true = torch.stack(y_true).cpu()

# Generar la matriz de confusión
conf_matrix = confusion_matrix(y_true, y_pred)

# Mostrar la matriz de confusión
plt.figure(figsize=(10, 8))
sns.heatmap(conf_matrix, annot=True, fmt='d', cmap='Blues', xticklabels=label_encoder.classes_, yticklabels=label_encoder.classes_)
plt.xlabel('Predicted')
plt.ylabel('True')
plt.title('Confusion Matrix')
plt.show()

# Calcular el F1-score
f1 = f1_score(y_true, y_pred, average='weighted')
print(f'F1 Score: {f1:.2f}')

# Definir el mapeo de números a etiquetas MBTI
mbti_labels = [
    "ENFJ",  # 0
    "ENFP",  # 1
    "ENTJ",  # 2
    "ENTP",  # 3
    "ESFJ",  # 4
    "ESFP",  # 5
    "ESTJ",  # 6
    "ESTP",  # 7
    "INFJ",  # 8
    "INFP",  # 9
    "INTJ",  # 10
    "INTP",  # 11
    "ISFJ",  # 12
    "ISFP",  # 13
    "ISTJ",  # 14
    "ISTP"   # 15
]

# Mostrar el mapeo
for i, label in enumerate(mbti_labels):
    print(f"{i}: {label}")