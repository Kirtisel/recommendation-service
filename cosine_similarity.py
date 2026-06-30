# -*- coding: utf-8 -*-
"""
Created on Fri Jun 26 11:41:41 2026

@author: AYSapunov
"""


import numpy as np
import pandas as pd
import json
import yaml
from sklearn.metrics.pairwise import cosine_similarity
from prepare_rnd_forest_data import check_business


TAGS = ["Семья/Дети", "Романтика/Пары", "Бизнес", "Премиум", "Длительное проживание", "Компания мужчин"]

# База услуг 
services_data = {
    "Переговорные комнаты": [0.0, 0.0, 0.8, 0.1, 0.0, 0.0],
    "Прачечная": [0.8, 0.0, 0.1, 0.2, 0.8, 0.1],
    "Услуги фотостудии": [0.5, 0.0, 0.0, 0.0, 0.0, 0.0],
    "Заказ тортов": [0.6, 0.5, 0.0, 0.3, 0.3, 0.0],
    "Бильярд": [0.2, 0.1, 0.1, 0.0, 0.1, 0.5],
    "Печать документов": [0.0, 0.0, 0.5, 0.0, 0.1, 0.0]
}


def convert_to_list(x):
    # Проверяем: если это строка и она не пустая
    if isinstance(x, str) and x.strip():
        return json.loads(x)  # Превращает текст в список
    else:
        return x              # Иначе оставляет данные как есть (например, NaN или None)

def extract_tags_from_row(row):
    
    # Создаем пустой вектор (базовые нули для всех 5 тегов)
    vector = np.zeros(len(TAGS))

    # 1. Считаем длительность проживания в днях
    arrival = pd.to_datetime(row["ArrivalDate"])
    departure = pd.to_datetime(row["DepartureDate"])
    
    # arrival = arrival.tz_localize(None)
    # departure = departure.tz_localize(None)
    
    duration_days = (departure - arrival).days

    
    total_guests = int(row.get("GuestsCount", 1)) # если колонки нет или она пустая, код подставит 1
    children = int(row.get("ChildCount", 0))
    man = 0
    woman = 0
    guestsList = convert_to_list(row.get("guestsList"))
    
    for g in guestsList:
        if g.get("Sex") == "F":
            woman += 1
        elif g.get("Sex") == "M":
            man += 1
    
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    aggregators = config['aggregators']    
    is_bussines = check_business(row.get("CompanyProfileName"), aggregators)
    
    # Маркируем премиум-сегмент (номера с буквой X)
    is_premium = int('X' in str(row.get('RoomTypeCode', '')))
        
    
    # --- ЗАПОЛНЕНИЕ ТЕГОВ ---

    # Тег 0: Семья/Дети
    if children > 0:
        vector[0] = 1.0

    # Тег 1: Романтика/Пары
    if total_guests == 2 and children == 0 and man == 1 and woman == 1:
        vector[1] = 1.0

    # Тег 2: Бизнес
    

    if is_bussines == 1:
        vector[2] = 1.0
        vector[1] = 0.0  # Командировочным коллегам романтику не рекомендуем

    # Тег 3: Премиум
    if is_premium == 1:
        vector[3] = 1.0

    # Тег 4: Длительный отдых
    if duration_days >= 5:
        vector[4] = 1.0
        
    # Тег 5: Компания мужчин
    if man >= 2:
        vector[5] = 1.0

    return vector.reshape(1, -1)
    

def calculate(booking_vector, data):
    service_predict = {}
    
    for service_name, service_vector in data.items():
        # Превращаем список услуги в 2D массив для sklearn
        srv_vec_2d = np.array(service_vector).reshape(1, -1)
        
        # Считаем сходство
        similarity = cosine_similarity(booking_vector, srv_vec_2d)[0][0]
        
        if similarity >= 0.5:
            similarity = 1
        else:
            similarity = 0
        
        service_predict[service_name] = similarity
        
    return service_predict
    

def get_cos_sim_predictions(df):
    # Создаем пустой список, куда будем складывать результаты
    rows_list = []

    for index, row in df.iterrows():
        booking_vector = extract_tags_from_row(row)
        service_predict = calculate(booking_vector, services_data)

        # Создаем один словарь для текущего бронирования
        # Оператор ** распаковывает один словарь внутрь другого
        guest_data = {"Id": row["Id"], **service_predict}

        # Добавляем словарь в список
        rows_list.append(guest_data)

    # Собираем финальный датафрейм одним действием из списка словарей, это быстрее чем predict_df.at[index, key] = value
    predict_df = pd.DataFrame(rows_list)

    return predict_df
            
    
if __name__ == "__main__":
    
    from pathlib import Path
    from utils import save_dataframe_to_csv_file
    
    
    print (TAGS)
    csv_path = Path("D:/Admin/Documents/Учеба/Практика/тесты/test/csv_files") / "merged.csv"
    csv_dir = Path("D:/Admin/Documents/Учеба/Практика/тесты/test/predictions") 
    df = pd.read_csv(csv_path, sep=';')
    predict_df = get_cos_sim_predictions(df.head(100).copy())
    save_dataframe_to_csv_file(predict_df, csv_dir, "cos_sim_predictions.csv")
    
    
    

        