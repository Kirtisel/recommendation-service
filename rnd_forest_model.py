# -*- coding: utf-8 -*-
"""
Created on Sun Jun 21 14:34:30 2026

@author: Admin
"""

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

import pandas as pd
import pickle


def save_model_file(model, directory_path, file_name):
    full_path = directory_path / file_name
    
    # Открываем файл на запись ('wb' - write binary) и сохраняем модель
    with open(full_path, 'wb') as file:
        pickle.dump(model, file)
    
    return full_path


def load_model_from_file(path_to_file):
    with open(path_to_file, 'rb') as file:
       fitness_model = pickle.load(file) 
    return fitness_model


def show_feature_importance(model, df_fitness):
    print("\n=== Важность признаков для предсказания Фитнеса ===")
    
    # 1. Получаем имена признаков (все колонки, кроме целевой Fitness_order)
    feature_names = df_fitness.drop(columns=['Fitness_order']).columns
    
    # 2. Берем веса важности из обученной модели
    importances = model.feature_importances_
    
    # 3. Объединяем в красивую таблицу DataFrame
    importance_df = pd.DataFrame({
        'Признак': feature_names,
        'Важность (в %)': importances * 100  # переводим в проценты для наглядности
    })
    
    # 4. Сортируем по убыванию (самые важные — наверху)
    importance_df = importance_df.sort_values(by='Важность (в %)', ascending=False).reset_index(drop=True)
    
    # Выводим результат на экран с округлением до 2 знаков
    print(importance_df.round(2).to_string(index=False))
    
    return importance_df


def train_fitness_model(df_fitness):
    print("\n=== Обучение модели Random Forest для Фитнеса ===")
    
    # 1. Разделяем целевую переменную (y) и признаки для обучения (X)
    y = df_fitness['Fitness_order']
    X = df_fitness.drop(columns=['Fitness_order'])
    
    # 2. Делим данные на обучающую (80%) и тестовую (20%) выборки
    # stratify=y гарантирует одинаковый процент купивших фитнес в обеих выборках
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # 3. Настройка и запуск случайного леса
    # class_weight='balanced' помогает модели лучше находить редких покупателей фитнеса
    model = RandomForestClassifier(
        n_estimators=100, 
        random_state=42, 
        class_weight='balanced',
        max_depth=5  # ограничение глубины защитит от переобучения
    )
    model.fit(X_train, y_train)
    
    # 4. Проверка качества работы алгоритма через вероятности
  # Получаем вероятность класса 1 для каждого клиента
    probabilities = model.predict_proba(X_test)[:, 1]
  
  # Снижаем порог принятия решения до 15% (вместо стандартных 50%)
    custom_threshold = 0.15
    predictions = (probabilities >= custom_threshold).astype(int)
  
    print(f"=== Результаты с кастомным порогом {custom_threshold:.2f} ===")
    print(f"Общая точность (Accuracy): {accuracy_score(y_test, predictions):.4f}\n")
    print(classification_report(y_test, predictions))
    
    return model


# Запускаем обучение
if __name__ == "__main__":

    file_path = "D:/Admin/Documents/Учеба/Практика/тесты/fitness_data.csv"   # D:/Admin/Documents/Учеба/Практика/тесты/merged.csv
    df = pd.read_csv(file_path, sep=';')

