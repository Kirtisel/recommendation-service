# -*- coding: utf-8 -*-
"""
Created on Mon Jun 22 15:34:54 2026

@author: 1
"""
import pandas as pd

from pydantic import BaseModel, Field, model_validator         # Модели данных для валидации
from fastapi import FastAPI, HTTPException 
from datetime import date 

import multiprocessing
import uvicorn
         
import download as dl
from utils import create_directory, save_dataframe_to_csv_file
from prepare import get_files, create_csv
from prepare_rnd_forest_data import prepare_rnd_forest_data, prepare_fitness_prediction_data
from rnd_forest_model import load_model_from_file
from cosine_similarity import get_cos_sim_predictions


# pyinstaller --onedir main.py сборка в exe   pyinstaller --onedir --noconfirm --clean main.py


dl.load_config()
jsonl_dir = create_directory(dl.BASE_DIR, "logus_files")
csv_dir = create_directory(dl.BASE_DIR, "csv_files")
test_dir = create_directory(dl.BASE_DIR, "test")
test_path = test_dir / "test_merged.csv"
test_pr_path = test_dir / "test_predictions.csv"
csv_path = csv_dir / "merged.csv"

fitness_model = load_model_from_file(test_dir / "test_rf_fitness_model.pkl")

# =========================================================
#  ИНИЦИАЛИЗАЦИЯ И МОДЕЛИ ДАННЫХ
# =========================================================
app = FastAPI(title="Recommendation Service API") # uvicorn main:app --reload для тестов http://127.0.0.1:8000/docs

# Описываем входные данные
class GetRecommendations(BaseModel):
    arrival_date_from: date
    arrival_date_to: date
    @model_validator(mode='after')
    def validate_dates(self):
        if self.arrival_date_to < self.arrival_date_from:
            raise ValueError("Вторая дата должна быть больше первой")
        return self  # Это оставить обязательно
    
    
# Описываем входные данные для обучения (две даты, как мы планировали)
class GetTestRecommendations(BaseModel):
    # ge означает Greater than or Equal, le означает Less than or Equal
    test_arrival_date_from: date = Field(ge=date(2024, 1, 1), le=date(2025, 12, 31))
    test_arrival_date_to: date = Field(ge=date(2024, 1, 1), le=date(2025, 12, 31)) 
    
    @model_validator(mode='after')
    def validate_dates(self):
        if self.test_arrival_date_to < self.test_arrival_date_from:
            raise ValueError("Вторая дата должна быть больше первой")
        return self  # Это оставить обязательно


# Эндпоинт 1: Тест рекомендаций без подключения к серверу
@app.post("/GetTestPredictions")
def get_test_predictions(payload: GetTestRecommendations): 
    df = pd.read_csv(test_path, sep=';')
    
  
    df['ArrivalDate'] = pd.to_datetime(df['ArrivalDate'], errors='coerce')
    
    date_from = pd.Timestamp(payload.test_arrival_date_from).tz_localize('Etc/GMT-3')
    date_to = (pd.Timestamp(payload.test_arrival_date_to) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)).tz_localize('Etc/GMT-3')
    
    # print(type(date_from))
    df_pr = df[df['ArrivalDate'].between(date_from, date_to)]
    
    if df.empty:
        return df.to_dict(orient='records')
    
    df_cs = get_cos_sim_predictions(df_pr)
    
    # СЛУЧАЙНЫЙ ЛЕС
    df_rf = prepare_rnd_forest_data(df_pr, csv_dir) # ЗДЕСЬ ЛИШНИЙ 2 ПАРАМЕТР !!!
  
    df_fitness_to_predict = prepare_fitness_prediction_data(df_rf)
    # print(f"!!!!!!!!!!!!!!!!!!!!!{len(df_fitness_to_predict)}")
    df_fitness_to_predict = df_fitness_to_predict.drop(columns=['Fitness_order']) # удаляем целевую колонку
    # отправка данных в модель для получения предсказаний
    fitness_model = load_model_from_file(test_dir / "test_rf_fitness_model.pkl")
    pr = fitness_model.predict(df_fitness_to_predict)
    fit_predictions = pd.DataFrame({
        'Id': df_fitness_to_predict.index,
        'Фитнес': pr
    })
    
    df_cs['Id'] = df_cs['Id'].astype(int)
    fit_predictions['Id'] = fit_predictions['Id'].astype(int)
    merged_df = pd.merge(fit_predictions, df_cs, on="Id")
    # save_dataframe_to_csv_file(merged_df, test_dir, "test_predictions.csv")   
    
    # FastAPI возвращает только простые типы данных: строки, числа, словари (dict) или списки (list)
    # orient='records' каждая строка - словарь, если не указывать вернет каждую колонку в виде словаря 
    return merged_df.to_dict(orient='records')

# Эндпоинт 2: Получение рекомендаций из api Логус
@app.post("/GetPredictions")
def get_predictions(payload: GetRecommendations):
    delete_files(jsonl_dir)
    
    session = dl.auth()
    
    # Проверка работоспособности эндпоинта
    try:
        response = session.post(dl.url_quick_search, json={"ArrivalDateFrom":"2025-01-01", "ArrivalDateTo":"2025-01-02"})
        # Проверка HTTP-статуса (выдаст ошибку, если статус не 200)
        response.raise_for_status()
    except Exception as e:
        print(f"Ошибка при пробной загрузке бронирований: {e}")
        raise HTTPException(
            status_code=502,  # 502 - выступая в роли шлюза, получил недопустимый ответ от другого (внешнего) сервера
            detail='Файл с данными пуст, предсказания невозможны',  # Ваше сообщение
        )
        
    # В тесте этого блока нет =================================
       
    jsonl_file = dl.load_to_file(session, payload.arrival_date_from.strftime("%Y-%m-%d"), payload.arrival_date_to.strftime("%Y-%m-%d"), 50, 0, jsonl_dir)
        
    if jsonl_file.is_file() == False or jsonl_file.stat().st_size == 0: 
        return "В выбранном периоде заезды отсутствуют."
        
    dl.get_additional_info(jsonl_file)
    dl.get_postings_info(jsonl_file)
    list_jsonl = get_files(jsonl_dir, r"\d{4}-\d{2}-\d{2}--\d{4}-\d{2}-\d{2}\.jsonl")
    create_csv(list_jsonl, csv_path)
    
    # В тесте этого блока нет ================================= 
        
    
    df = pd.read_csv(csv_path, sep=';')
    
    
    
    df['ArrivalDate'] = pd.to_datetime(df['ArrivalDate'], errors='coerce')
    df_pr = df
    df_cs = get_cos_sim_predictions(df_pr)
    
    # СЛУЧАЙНЫЙ ЛЕС
    df_rf = prepare_rnd_forest_data(df_pr, csv_dir) # ЗДЕСЬ ЛИШНИЙ 2 ПАРАМЕТР !!!
    df_fitness_to_predict = prepare_fitness_prediction_data(df_rf)
    df_fitness_to_predict = df_fitness_to_predict.drop(columns=['Fitness_order']) # удаляем целевую колонку
    # отправка данных в модель для получения предсказаний
    # fitness_model = load_model_from_file(test_dir / "test_rf_fitness_model.pkl") # ЗАГРУЖАТЬ ПРИ СТАРТЕ СЕРВИСА
    pr = fitness_model.predict(df_fitness_to_predict)
    fit_predictions = pd.DataFrame({
        'Id': df_fitness_to_predict.index,
        'Фитнес': pr
    })
    
    df_cs['Id'] = df_cs['Id'].astype(int)
    fit_predictions['Id'] = fit_predictions['Id'].astype(int)
    merged_df = pd.merge(fit_predictions, df_cs, on="Id")
    save_dataframe_to_csv_file(merged_df, test_dir, "test_predictions.csv")   
    
    # FastAPI возвращает только простые типы данных: строки, числа, словари (dict) или списки (list)
    # orient='records' каждая строка - словарь, если не указывать вернет каждую колонку в виде словаря 
    return merged_df.to_dict(orient='records')


def delete_files(path_dir):
    for item in path_dir.iterdir():
        if item.is_file():
            item.unlink()
            
    
# ЭТОТ БЛОК ДОЛЖЕН БЫТЬ В САМОМ КОНЦЕ ФАЙЛА main.py:
if __name__ == '__main__':
    multiprocessing.freeze_support()
    
    print("Запуск веб-сервера Рекомендаций...")
    # Передаем сам объект app вместо строки "main:app"
    uvicorn.run(app, dl.host, dl.port) 