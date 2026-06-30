# -*- coding: utf-8 -*-
"""
Created on Wed Jun  3 11:29:01 2026

@author: AYSapunov
"""
import pandas as pd
import json
import csv
import os
from pathlib import Path
import re  # Импортируем модуль для регулярных выражений
import ast



def load_from_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as file:
    # Загружаем данные в переменную (обычно это словарь или список)
            data = json.load(file)
            df = pd.DataFrame(data)
            print(df.head())
            print(df.iloc[-1])
            print(df.info())
            return df
    except Exception as e:
        print(f"Ошибка: {e}")
        
        
def load_from_jsonl(path):
    df = pd.read_json(path, lines=True)          
    print(df.head())
    # print(df.iloc[-1])
    print(df.info())
    return df
  
    
def jsonl_to_json(path):
# Читаем JSONL
    data = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    
    # Вместо pd.DataFrame(data) используем нормализацию
    # Она корректно обработает разные ключи и вложенность
    df = pd.json_normalize(data)
    print(df.info())
    
    #output_path = path.replace('.jsonl', '.json')
    #df.to_json(output_path, orient='records', force_ascii=False, indent=4)
    #print(f"Готово! Сохранено в {output_path}")


def prepare_data(df):
    # Удалить колонки, где ВСЕ значения пустые (NaN)
    df = df.dropna(axis=1, how='all')
    cols_to_drop = [
    'Notes', 'CreatedUser', 'ModifiedUser', 
    'PublishDate'
    ]

    # Удаляем
    df = df.drop(columns=cols_to_drop, errors='ignore')
    return df


# ищет строку в многострочном jsonl файле по id
def get_row_byId (path, id_row):
    target_row = None
    with open(path, 'r', encoding='utf-8') as f_info:
        for line in f_info:
            line = line.strip()
            if line:
            # Читаем строку как словарь
                full_row = json.loads(line)
            
            # Проверяем ID (приводим к одному типу, например, к строке, чтобы избежать багов)
                if str(full_row.get('Id')) == str(id_row):
                    target_row = full_row
                    break  # Нашли нужную строку, останавливаем цикл, чтобы не читать файл дальше

# Проверяем результат
    #if target_row:
        #print("Строка найдена:")
    #else:
        #print(f"Строка с id {id_row} не найдена в файле.")
    
    return target_row
    


    

# Подготавливаем данные из jsonl бронирований, который получены вызовом QuickSearch  
def prepare_jsonl(path_jsonl, path_csv):
    file_exists = os.path.isfile(path_csv)
    
    # -------------------------------------------------------------------------
    # ШАГ 1: Загружаем весь файл _info в память ОДИН раз (Индексация)
    # -------------------------------------------------------------------------
    res_info_jsonl = path_jsonl.replace(".", "_info.")
    info_cache = {}  # Сюда сохраним всё в формате { 'ID': словарь_с_гостями }
    
    print("Индексация файла со сведениями о гостях... Пожалуйста, подождите.")
    if os.path.isfile(res_info_jsonl):
        with open(res_info_jsonl, 'r', encoding='utf-8') as f_info:
            for line in f_info:
                line = line.strip()
                if line:
                    full_row = json.loads(line)
                    info_id = full_row.get('Id')
                    if info_id is not None:
                        # Сохраняем под строковым ключом для надежности сравнения
                        info_cache[str(info_id)] = full_row
    print(f"Индексация завершена. Успешно загружено {len(info_cache)} строк.")
    # -------------------------------------------------------------------------
    
    # ШАГ 2: Основной цикл по бронированиям
    with open(path_jsonl, 'r', encoding='utf-8') as f:
        for line in f:
            rows = []
            line = line.strip()
            if line:
                full_row = json.loads(line)
                id_res = full_row.get('Id')
                
                res_data = {
                    'Id': id_res,
                    'CreatedDate': full_row.get('CreatedDate'),
                    'ArrivalDate': full_row.get('ArrivalDate'),
                    'DepartureDate': full_row.get('DepartureDate'),
                    'DepositAmount': full_row.get('DepositAmount'),
                    'PaymentsSum': full_row.get('PaymentsSum'),                    
                    'CompanyProfileName': full_row.get('CompanyProfileName'),
                    'PayingCompanyName': full_row.get('PayingCompanyName'),
                    'GuestsCount': full_row.get("Layout", {}).get("GuestsCount"),
                    'AdultCount': full_row.get("Layout", {}).get("AdultCount"), 
                    'ChildCount': (
                       int(full_row.get("Layout", {}).get("Child1Count", 0)) + int(full_row.get("Layout", {}).get("Child2Count", 0)) + 
                       int(full_row.get("Layout", {}).get("Child3Count", 0)) + int(full_row.get("Layout", {}).get("Child4Count", 0)) + 
                       int(full_row.get("Layout", {}).get("Child5Count", 0))
                    ),
                    'Status': full_row.get('Status'),
                    'RoomTypeCode': full_row.get('RoomTypeCode'), 
                    'RateCode': full_row.get('RateCode'),
                    'RoomNo': full_row.get('RoomNo'), 
                    'MarketSegmentId': full_row.get('MarketSegmentId'),
                }
                
                # ИСПРАВЛЕНО: Вместо долгого чтения с диска, мгновенно берем строку из памяти
                info_row = info_cache.get(str(id_res))
                
                guestsList = []
                if info_row is not None:
                    guests = info_row.get("ReservationGuests", [])
                    guestIndex = 1
                    for g in guests:
                        guestsList.append({
                            "index": guestIndex,
                            "FirstName": g.get("FirstName"),
                            "MiddleName": g.get("MiddleName"),
                            "LastName": g.get("LastName"),
                            "Sex": g.get("Sex"),
                            "BirthDate": g.get("BirthDate"),
                            "CitizenshipCountryCode": g.get("CitizenshipCountryCode"),
                            "ProfileGenericNo": g.get("ProfileGenericNo"),
                            "Email": g.get("Email"),
                            "VehicleInfo": g.get("VehicleInfo"),
                        })
                        guestIndex = guestIndex + 1
                  
                res_data["guests"] = json.dumps(guestsList, ensure_ascii=False) if guestsList else "[]"
                rows.append(res_data)
                
                fields = list(rows[0].keys())
                with open(path_csv, 'a', newline='', encoding='utf-8-sig') as f_csv:
                    writer = csv.DictWriter(f_csv, fieldnames=fields, delimiter=';')
                    
                    if not file_exists:
                        writer.writeheader()   
                        file_exists = True
                        
                    writer.writerows(rows)
                
          



def reservation_df(path_jsonl):    
    rows = []
    
    #Основной цикл по бронированиям
    with open(path_jsonl, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                full_row = json.loads(line)
                id_res = full_row.get('Id')
                
                res_data = {
                    'Id': id_res,
                    'CreatedDate': full_row.get('CreatedDate'),
                    'ArrivalDate': full_row.get('ArrivalDate'),
                    'DepartureDate': full_row.get('DepartureDate'),
                    'DepositAmount': full_row.get('DepositAmount'),
                    'PaymentsSum': full_row.get('PaymentsSum'),                    
                    'CompanyProfileName': full_row.get('CompanyProfileName'),
                    'PayingCompanyName': full_row.get('PayingCompanyName'),
                    'GuestsCount': full_row.get("Layout", {}).get("GuestsCount"),
                    'AdultCount': full_row.get("Layout", {}).get("AdultCount"), 
                    'ChildCount': (
                       int(full_row.get("Layout", {}).get("Child1Count", 0)) + int(full_row.get("Layout", {}).get("Child2Count", 0)) + 
                       int(full_row.get("Layout", {}).get("Child3Count", 0)) + int(full_row.get("Layout", {}).get("Child4Count", 0)) + 
                       int(full_row.get("Layout", {}).get("Child5Count", 0))
                    ),
                    'Status': full_row.get('Status'),
                    'RoomTypeCode': full_row.get('RoomTypeCode'), 
                    'RateCode': full_row.get('RateCode'),
                    'RoomNo': full_row.get('RoomNo'), 
                    'MarketSegmentId': full_row.get('MarketSegmentId'),
                    'FolioId': full_row.get('FolioId'),
                }
                                            
                rows.append(res_data)
                
        df = pd.DataFrame(rows)    
        #df.to_csv(path_csv, index=False, encoding="utf-8-sig", sep=";")
        return df
            


def info_df(path_jsonl):    
    rows = []
    
    #Основной цикл по бронированиям
    with open(path_jsonl, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                full_row = json.loads(line)
                id_res = full_row.get('Id')
                guestsList = []
                guests = full_row.get("ReservationGuests", [])
                
                guestIndex = 1
                for g in guests:
                    guestsList.append({
                        "index": guestIndex,
                        "FirstName": g.get("FirstName"),
                        "MiddleName": g.get("MiddleName"),
                        "LastName": g.get("LastName"),
                        "Sex": g.get("Sex"),
                        "BirthDate": g.get("BirthDate"),
                        "CitizenshipCountryCode": g.get("CitizenshipCountryCode"),
                        "ProfileGenericNo": g.get("ProfileGenericNo"),
                        "Email": g.get("Email"),
                        "VehicleInfo": g.get("VehicleInfo"),
                    })
                    guestIndex = guestIndex + 1
            
                data = {
                    "Id": id_res,
                    # превращаем список в правильный JSON-текст.
                    # ensure_ascii=False сохраняет русские буквы читаемыми, а не в виде \u0430
                    "guestsList": json.dumps(guestsList, ensure_ascii=False),
                    }
            
                rows.append(data)
                
    df = pd.DataFrame(rows)
    return df    
    #df.to_csv(path_csv, index=False, encoding="utf-8-sig", sep=";")
        
    
    
def postings_df(path_jsonl, path_csv):    
    rows = []
    
    #Основной цикл по бронированиям
    with open(path_jsonl, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                full_row = json.loads(line)
                id_folio = full_row.get('Id')
                services = []
                folio_services = []
                str_services = None
                str_fol_serv = None
                
                
                if full_row.get("Services"):
                    services = full_row.get("Services", [])
                    str_services = json.dumps(services, ensure_ascii=False)
                    
                if full_row.get("FolioServices"):
                    folio_services = full_row.get("FolioServices", [])
                    str_fol_serv = json.dumps(folio_services, ensure_ascii=False)
                    
                data = {
                    "FolioId": id_folio,
                    "FolioServicesAmount": full_row.get("FolioServicesAmount"),
                    # превращаем список в правильный JSON-текст.
                    # ensure_ascii=False сохраняет русские буквы читаемыми, а не в виде \u0430
                    "Services": str_services,
                    "FolioServices":str_fol_serv,               
                    }
                
                rows.append(data)            
    
    df = pd.DataFrame(rows)
    df.to_csv(path_csv, index=False, encoding="utf-8-sig", sep=";")
    return df    
        
def postings_df1(path_jsonl):    
    rows = []
    
    #Основной цикл по бронированиям
    with open(path_jsonl, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                full_row = json.loads(line)
                id_folio = full_row.get('Id')
                pockets_services  = []
                
                
                if full_row.get("Pockets"):
                    for pocket in full_row["Pockets"]:
                    # Заходим в начисления каждого кармана (ОСН, ЮРЛ, ДОП и т.д.)
                        postings = pocket.get("Postings")
                        if postings:
                            for post in postings:
                            # Извлекаем код и название начисления
                                code = post.get("Code")
                                name = post.get("Name", "Неизвестное начисление")
                                pockets_services.append(f"Code: {code}")
                
                data = {
                    "FolioId": id_folio,
                    "FolioServicesAmount": full_row.get("FolioServicesAmount"),
                    # превращаем список в правильный JSON-текст.
                    # ensure_ascii=False сохраняет русские буквы читаемыми, а не в виде \u0430
                    "PocketsServicesCount": len(pockets_services), 
                    "Services": json.dumps(pockets_services, ensure_ascii=False) if pockets_services else None,
                    }
                
                rows.append(data)            
    
    df = pd.DataFrame(rows)
    #df.to_csv(path_csv, index=False, encoding="utf-8-sig", sep=";",quoting=csv.QUOTE_NONNUMERIC, escapechar="\\")
    return df     

        
    
def create_csv(path_list, csv_path):
    
    data = []
    
    
    for path in path_list:
        # info_path = path.replace(".", "_info.")  
        info_path = path.with_stem(f"{path.stem}_info")
        # post_path = path.replace(".", "_postings.")
        post_path = path.with_stem(f"{path.stem}_postings")
        res_df = reservation_df(path)
        info_res_df = info_df(info_path)
        pos_df = postings_df1(post_path)
        res_df['Id'] = res_df['Id'].astype(int)
        info_res_df['Id'] = info_res_df['Id'].astype(int)
        merged_df = pd.merge(res_df, info_res_df, on="Id")
        merged_df['FolioId'] = merged_df['FolioId'].astype(int)
        pos_df['FolioId'] = pos_df['FolioId'].astype(int)
        merged_df = pd.merge(merged_df, pos_df, on="FolioId")
        
        data.append(merged_df)
        
    df = pd.concat(data, ignore_index=True)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig", sep=";")
        


#get_files ("D:/Admin/Documents/Учеба/Практика/тесты", r"\d{4}-\d{2}-\d{2}--\d{4}-\d{2}-\d{2}\.jsonl")


#r"data_\d{4}-\d{2}-\d{2}\.jsonl"
def get_files(path, pattern):    
    list_paths = []
    path_obj = Path(path)

    for item in path_obj.iterdir():
        
        #Если текущий объект — это файл (а не папка)
        if item.is_file():
            if re.match(pattern, item.name):
                # list_paths.append(str(item))
                list_paths.append(item)

    # print(list_paths)
    return list_paths 


# функция для обработки одной ячейки
def convert_to_list(x):
    # Проверяем: если это строка и она не пустая
    if isinstance(x, str) and x.strip():
        return json.loads(x)  # Превращает текст в список
    else:
        return x              # Иначе оставляет данные как есть (например, NaN или None)

#подготовка данных о людях
def get_people_df(df):
    # print("Тип данных в ячейке:", type(df["guestsList"].dropna().iloc[0]))
    # print("Сам элемент:", df["guestsList"].dropna().iloc[0])
    
    # 1. Оживляем текст: переводим JSON-строки в реальные списки Python
    # Функция json.loads идеально понимает "null", поэтому ошибок не будет
    # df["guestsList"] = df["guestsList"].apply(
    #     lambda x: json.loads(x) if isinstance(x, str) and x.strip() else x
    # )
    
    df["guestsList"] = df["guestsList"].apply(convert_to_list)
    # Разворачиваем списки гостей на отдельные строки
    df_exploded = df.explode("guestsList").reset_index(drop=True) 
    #  Извлекаем ключи словарей из колонки в отдельные полноценные колонки
    df_guests = pd.json_normalize(df_exploded["guestsList"])
    df_exploded = df_exploded.drop(columns=["guestsList"])
    # Шаг 3: Соединяем исходные данные строки с новыми колонками гостей
    df_final = pd.concat([df_exploded, df_guests], axis=1)
    
    return df_final
    





if __name__ == "__main__":
 
    list_jsonl = get_files("D:/Admin/Documents/Учеба/Практика/тесты", r"\d{4}-\d{2}-\d{2}--\d{4}-\d{2}-\d{2}\.jsonl")        
    csv_path = "D:/Admin/Documents/Учеба/Практика/тесты/merged.csv"
    create_csv(list_jsonl, csv_path)
    print(list_jsonl)






"""
res_df = reservation_df("D:/Admin/Documents/Учеба/Практика/тесты/2025-01-01--2025-03-31.jsonl", "D:/Admin/Documents/Учеба/Практика/тесты/reservations.csv")
info_res_df = info_df("D:/Admin/Documents/Учеба/Практика/тесты/2025-01-01--2025-03-31_info.jsonl", "D:/Admin/Documents/Учеба/Практика/тесты/info.csv")
pos_df = postings_df1("D:/Admin/Documents/Учеба/Практика/тесты/2025-01-01--2025-03-31_postings.jsonl", "D:/Admin/Documents/Учеба/Практика/тесты/postings.csv")
res_df['Id'] = res_df['Id'].astype(int)
info_res_df['Id'] = info_res_df['Id'].astype(int)
merged_df = pd.merge(res_df, info_res_df, on="Id")
merged_df['FolioId'] = merged_df['FolioId'].astype(int)
pos_df['FolioId'] = pos_df['FolioId'].astype(int)
merged_df = pd.merge(merged_df, pos_df, on="FolioId")
merged_df.to_csv("D:/Admin/Documents/Учеба/Практика/тесты/merged.csv", index=False, encoding="utf-8-sig", sep=";")
"""
#postings_df1("D:/Admin/Documents/Учеба/Практика/тесты/2025-01-01--2025-03-31_postings.jsonl", "D:/Admin/Documents/Учеба/Практика/тесты/postings.csv")


