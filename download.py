# -*- coding: utf-8 -*-
"""
Created on Wed Jun  3 11:27:28 2026

@author: AYSapunov
"""

"""
Редактор Spyder

Это временный скриптовый файл.
"""


"""
#%% Шаг 2: Тестирование функций
# Выделите этот блок и нажмите Shift+Enter для запуска только этой части
можно запускать каждый блок отдельно (клавишами Shift + Enter), демонстрируя работу
программы пошагово

Ctrl + I (или Cmd + I) документация

"""
import sys
import requests
import time
import json
from datetime import datetime, timezone
import zoneinfo
import yaml
from pathlib import Path


# ОПРЕДЕЛЯЕМ БАЗОВУЮ ПАПКУ (где лежит .exe или .py)
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent        # Папка с файлом .exe
else:
    BASE_DIR = Path(__file__).resolve().parent    # Папка со скриптом .py


token = None
url_ping = None
url_quick_search = None
url_search = None
url_reservation = None
url_folio = None
program_path = None
session = None
host = None
port = None




# --- ИСПОЛЬЗОВАНИЕ ---

# Находим путь к YAML файлу
config_path = BASE_DIR / "config.yaml" # укажите ваше точное имя файла

def load_config():
    global program_path, token, url_ping, url_quick_search, url_search, \
        url_reservation, url_folio, session, host, port
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
     
    # program_path = Path(config['program_path'])
    token = config['token']
    url_ping = config['url_ping']
    # url_dictionaries = config['url_dictionaries']
    url_quick_search = config['url_quick_search']
    url_search = config['url_search']
    url_reservation = config['url_reservation']
    url_folio = config['url_folio']
    
    #uvicorn server
    host = config["host"] # используется в main
    port = config["port"] # используется в main
    
def auth():
    global session
    session = requests.Session()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
        }
    session.headers = headers
   
    try:
       response = session.get(url_ping)
       print(response.status_code)
       response.raise_for_status() #превращает неудачные ответы сервера в ошибки
       # if response.status_code == 200:
       #     print("доступен", response.status_code)
       #     return True;
     
    except Exception as e:
        print(f"Сервер недоступен. Ошибка: {e}")
        return None
    
    return session

#Переводим Московское время в UTC, принимает строку в формате ISO 8601
def get_utc_time(moscowTime):
    dt = datetime.fromisoformat(moscowTime).replace(
    tzinfo=zoneinfo.ZoneInfo("Europe/Moscow"))
    dt_utc = dt.astimezone(timezone.utc)
    #print(dt_utc)
    return dt_utc.isoformat(timespec="seconds")     

#использует POST /api/Reservation/QuickSearch
def load_to_file(session, arrivalDateFrom, arrivalDateTo, limit, skip, path):
    fname = Path(path) / f"{arrivalDateFrom}--{arrivalDateTo}.jsonl"
    date_from_str = str(arrivalDateFrom).replace(":", "-")
    date_to_str = str(arrivalDateTo).replace(":", "-")
    # Путь к файлу чтобы : не сломало код
    fname = Path(path) / f"{date_from_str}--{date_to_str}.jsonl"
    arrivalDateFrom = get_utc_time(arrivalDateFrom)
    arrivalDateTo = get_utc_time(arrivalDateTo)
    params = {"ArrivalDateFrom": arrivalDateFrom,
  "ArrivalDateTo": arrivalDateTo
        }
    count = 0
    print (fname)
    
    while True:
        params.update({"Limit": limit, "Skip": skip})
        try:
            response = session.post(url_quick_search, json=params)
            data = response.json()
            
            if not data or len(data) == 0:
                break
            
            print(f"Получено записей: {len(data)}")
            count += 1
        
            with open(fname, "a", encoding = "utf-8") as f:
                for booking in data:
                    json_record = json.dumps(booking, ensure_ascii = False)
                    f.write(json_record + "\n")
                
            # all_records.extend(data)
            skip = skip + limit
        
        except Exception as e:
            print(f"Ошибка: {e}")
            break
    
    # if(count == 0):
    #     raise ValueError ("Нет данных в ответе Логус")
       
    print(f"Загрузка завершена, загружено {count} записей")
    return fname


#для каждого GenericNo из списка скачивает доп информацию по бронированию additional_info_dataframe

#получает список ключей из файла jsonl
def get_keys_list(target_key, jsonlPath):
    #jsonlInfo = jsonlPath.replace(".", "_info.")
    keys_list = []
    
    with open(jsonlPath, 'r', encoding='utf-8') as f:
        for line in f:
        # Убираем пробелы по краям и проверяем, что строка не пустая
            clean_line = line.strip()
            if clean_line:
            # Превращаем строку в Python-словарь
                obj = json.loads(clean_line)
                # Извлекаем значение по ключу (используем .get(), чтобы избежать ошибок, если ключа нет)
                if target_key in obj:
                    keys_list.append(obj[target_key])
    return keys_list


#для каждого ключа из листа выполняет запрос по url+key и записывает в файл
def get_info(keys_list, url, fname):
    success_count = 0
    with open(fname, "a", encoding = "utf-8") as f:
        
        for key in keys_list:
            try:
                response = session.get(url + f"/{key}")
                data = response.json()
            
                if not data or len(data) == 0:
                    break
   
                json_record = json.dumps(data, ensure_ascii = False)
                f.write(json_record + "\n")
                
                success_count += 1
                if success_count % 10 == 0:
                    print(f"Успешно записано элементов: {success_count}")
                    time.sleep(0.3)
                             
            except Exception as e:
               print(f"Ошибка: {e} key = {key}")
               
    print(f"Всего записано элементов: {success_count}")
                   

#для jsonl с информацией о бронированиях скачивает отдельный jsonl с расширенной информацией по каждому бронированию  
#файлы связаны по GenericNo
def get_additional_info(reservation_jsonl): 
    print("Загрузка дополнительной информации о бронированиях")
    #reservation_jsonl.stem — берет чистое имя файла без расширения (например, "res_postings") f"{...}_info" — добавляет к нему хвостик, получая "res_postings_info"..with_stem(...) — создает новый объект пути, заменяя старое имя на новое, но бережно сохраняя расширение .jsonl .
    res_info = reservation_jsonl.with_stem(f"{reservation_jsonl.stem}_info")
    keys_list = get_keys_list("GenericNo", reservation_jsonl)
    get_info(keys_list, url_reservation, res_info)
    print("Дополнительная информация о бронированиях загружена")
    
    return res_info

#для jsonl с информацией о бронированиях скачивает отдельный jsonl с расширенной информацией по каждому бронированию  
#файлы связаны по GenericNo
def get_postings_info(reservation_jsonl): 
    print("Загрузка информации о заказанных услугах")
    res_info = reservation_jsonl.with_stem(f"{reservation_jsonl.stem}_postings")
    keys_list = get_keys_list("GenericNo", reservation_jsonl)
    get_info(keys_list, url_folio, res_info)
    print("Информация о заказанных услугах загружена")
    return res_info
    
    
def count_lines (path):
    with open(path, "r", encoding="utf-8") as f:
        count = sum(1 for line in f)
    return count

    

