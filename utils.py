# -*- coding: utf-8 -*-
"""
Created on Wed Jun 10 06:35:53 2026

@author: Admin
"""
import json
from pathlib import Path
import yaml

def save_dataframe_to_csv_file(dataframe, directory_path, file_name):
    # Автоматически и безопасно собирает полный путь к файлу
    csv_path = directory_path / file_name
    dataframe.to_csv(csv_path, index=False, sep=';', encoding='utf-8-sig')
    
    return csv_path


def create_directory(path, directory):
    new_path = Path(path) / directory

    if new_path.exists():
        print(f"Папка {directory} на месте!")
    else:
        print(f"Папки {directory} нет, создаю...")
        new_path.mkdir(parents=True)
    
    return new_path




def jsonl_to_json (input_jsonl):
    output_json = input_jsonl.replace(".jsonl", ".json")
    with open(input_jsonl, "r", encoding="utf-8") as infile, \
         open(output_json, "w", encoding="utf-8") as outfile:
             
        # Начинаем обычный JSON-массив
        outfile.write("[\n")
        first = True
        for line in infile:
            line = line.strip()
            if not line:
                continue  # Пропускаем пустые строки
                
            if not first:
                outfile.write(",\n")  # Разделяем элементы запятой
            else:
                first = False
                
             # Превращаем текст строки в объект Python
            data = json.loads(line)
        
            # Превращаем объект в красивый JSON с отступами (4 пробела)
            # ensure_ascii=False сохраняет русский текст читаемым (не превращает в \u0430)
            formatted_json = json.dumps(data, indent=4, ensure_ascii=False)
        
            # Сдвигаем каждую строчку объекта вправо, чтобы внутри массива [ ] всё выглядело ровно
            indented_json = "\n".join("    " + l for l in formatted_json.splitlines())
        
            outfile.write(indented_json)
            
        # Закрываем JSON-массив
        outfile.write("\n]")


def l_config():
    global program_path, token, url_ping, url_dictionaries, url_quick_search, url_search, \
        url_reservation, url_folio
    
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # program_path = config['program_path'].replace("\\", "/") 
    program_path = Path(config['program_path'])
    token = config['token']
    url_ping = config['url_ping']
    url_dictionaries = config['url_dictionaries']
    url_quick_search = config['url_quick_search']
    url_search = config['url_search']
    url_reservation = config['url_reservation']
    url_folio = config['url_folio']
    

    
if __name__ == "__main__":    
    path = "D:/Admin/Documents/Учеба/Практика/тесты/res.jsonl"
    path1 = "D:/Admin/Documents/Учеба/Практика/тесты/res_info.jsonl"
    path2 = "D:/Admin/Documents/Учеба/Практика/тесты/res_postings.jsonl"
#jsonl_to_json (path)   
#jsonl_to_json (path1)   
    jsonl_to_json (path2)   


    