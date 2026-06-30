# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 22:14:15 2026

@author: Admin
"""
import pandas as pd
import yaml
import os
import re


def save_dataframe_to_csv_file(dataframe, directory_path, file_name):
    # Автоматически и безопасно собираем полный путь к файлу
    csv_path = os.path.join(directory_path, file_name)
    dataframe.to_csv(csv_path, index=False, sep=';', encoding='utf-8-sig')
    
    return csv_path


# Функция для проверки: бизнес это или агрегатор
def check_business(company_name, aggregators):
    name_lower = str(company_name).lower()
    
    # Если компании нет (физлицо), то это не бизнес-поездка
    if name_lower == 'no_company':
        return 0
        
    # Если в названии есть имя известного агрегатора — это НЕ прямой бизнес (0)
    if any(agg in name_lower for agg in aggregators):
        return 0
        
    # Во всех остальных случаях считаем, что это прямая компания / бизнес-поездка (1)
    return 1


# 2. Создаем числовой признак "Вместимость номера" (Capacity)
# Если код начинается на S (Single) -> 1 место, на D (Double) -> 2 места, на T (Triple) -> 3 места
def get_capacity(room):
    room_str = str(room).upper()
    if room_str.startswith('S'):
        return 1
    elif room_str.startswith('D'):
        return 2
    elif room_str.startswith('T'):
        return 3
    else:
        return 0 # на случай непредвиденных кодов
    

def get_rack_discount(rate):
    rate_str = str(rate).upper()
    if 'RACK' in rate_str:
        # Ищем цифры в названии тарифа с помощью регулярного выражения
        match = re.search(r'\d+', rate_str)
        return int(match.group()) if match else 0
    return 0 # для тарифов LONG, INI и др. скидку по умолчанию считаем 0


def prepare_rnd_forest_data(dataframe, csv_path):
    dataframe = dataframe.copy()  # Делает таблицу полностью независимой в памяти
    csv_path = csv_path / "random_forest_data.csv"
    #Переводим столбцы в правильный формат даты Pandas
    date_cols = ['CreatedDate', 'ArrivalDate', 'DepartureDate']
    for col in date_cols:
        dataframe[col] = pd.to_datetime(dataframe[col], errors='coerce')
    
   # Сколько дней между бронированием и приездом
    # Сбрасываем время до 00:00:00 у обеих дат, а затем считаем разницу в днях
    dataframe['Days_Before_Arrival'] = (pd.to_datetime(dataframe['ArrivalDate']).dt.tz_localize(None).dt.normalize() - pd.to_datetime(dataframe['CreatedDate']).dt.tz_localize(None).dt.normalize()).dt.days
    # dataframe['Days_Before_Arrival'] = (pd.to_datetime(dataframe['ArrivalDate']).dt.normalize() - pd.to_datetime(dataframe['CreatedDate']).dt.normalize()).dt.days
# 2. Если значение пустое (NaN), заполняем его нулем
    dataframe['Days_Before_Arrival'] = dataframe['Days_Before_Arrival'].fillna(0)

# 3. Если значение получилось меньше 0, принудительно превращаем его в 0
    dataframe['Days_Before_Arrival'] = dataframe['Days_Before_Arrival'].clip(lower=0)

# 4. Переводим в чистый целочисленный тип (int), чтобы Random Forest работал быстрее
    dataframe['Days_Before_Arrival'] = dataframe['Days_Before_Arrival'].astype(int)


# Сколько дней длится поездка (длительность проживания)
    dataframe['Stay_Duration'] = (dataframe['DepartureDate'].dt.tz_localize(None) - dataframe['ArrivalDate'].dt.tz_localize(None)).dt.days

# 3. Извлекаем сезонность из даты прибытия (ArrivalDate)
# Месяц (от 1 до 12) — поможет понять сезон (лето/зима)
    dataframe['Arrival_Month'] = dataframe['ArrivalDate'].dt.month

# День недели (0 - понедельник, 6 - воскресенье) — заезды в выходные часто отличаются
    dataframe['Arrival_DayOfWeek'] = dataframe['ArrivalDate'].dt.dayofweek

# 4. Удаляем исходные столбцы-даты, так как модель их не примет
    dataframe = dataframe.drop(columns=date_cols)

# Заполняем NaN нулями, а существующие суммы сохраняем
    dataframe['DepositAmount'] = dataframe['DepositAmount'].fillna(0)  
    
    # модифицируем колонку CompanyProfileName определяем является ли бизнес-поездкой или нет
    # загружаем список агрегаторов из конф. файла
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    aggregators = config['aggregators']
    
    # x — имя компании из строки, aggregators — переменная из yaml файла
    dataframe['isBusiness'] = dataframe['CompanyProfileName'].apply(lambda x: check_business(x, aggregators))
    dataframe = dataframe.drop(columns=['CompanyProfileName'])
    
    # 6. Целенаправленное кодирование колонки Status
# Создаем 3 новые числовые колонки (0 или 1) на основе значений в Status
    dataframe['Status_out'] = (dataframe['Status'] == 'OUT').astype(int)
    dataframe['Status_cancel'] = (dataframe['Status'] == 'CANCEL').astype(int)
    dataframe['Status_noshow'] = (dataframe['Status'] == 'NOSHOW').astype(int)

# Удаляем старую текстовую колонку Status, так как мы её полностью перенесли в числа
    dataframe = dataframe.drop(columns=['Status'])
    """
    # 8. Умное кодирование колонки RateCode (Кодирование частотой / Популярностью)
    
    dataframe['RateCode'] = dataframe['RateCode'].fillna('Unknown')
    
    # 1. Считаем, как часто встречается каждый тариф (в процентах от 0 до 1)
    rate_frequencies = dataframe['RateCode'].value_counts(normalize=True)
    
    # 2. Заменяем текст на эти числовые значения частоты
    dataframe['RateCode_Frequency'] = dataframe['RateCode'].map(rate_frequencies)
    
    # 3. Удаляем старый текстовый столбец
    dataframe = dataframe.drop(columns=['RateCode'])
    
    print("Колонка RateCode успешно сжата в один числовой признак популярности!")
    """
    dataframe = dataframe.drop(columns=['RoomNo'], errors='ignore')
    # Удаляем MarketSegmentId, так как частотное кодирование не передает логику категорий
    dataframe = dataframe.drop(columns=['MarketSegmentId'], errors='ignore')
    dataframe = dataframe.drop(columns=['FolioId'], errors='ignore')
    dataframe = dataframe.drop(columns=['guestsList'], errors='ignore')
    
    # 1. Берем данные из 'services' и превращаем в текст, чтобы компьютер мог искать в них коды
    services_str = dataframe['Services'].astype(str)

# 2. Создаем ПЕРВУЮ новую колонку 'target_4500' в вашей таблице
    dataframe['Fitness_order'] = services_str.str.contains('4500').astype(int)

# 3. Создаем ВТОРУЮ новую колонку 'target_2000' в вашей таблице
    dataframe['Breakfast_order'] = services_str.str.contains('2000').astype(int)
    
    # Id уходит из колонок в индекс
    dataframe = dataframe.set_index('Id')

# 4. Удаляем старую сложную колонку 'services'
    dataframe = dataframe.drop(columns=[#"Id",
                                        "PaymentsSum", # утечка данных из будущего для модели
                                        "FolioServicesAmount", # утечка данных из будущего для модели 
                                        "PocketsServicesCount", # есть бинарный флаг на заказ фитнеса и завтрака
                                        "Services",
                                        "PayingCompanyName", # есть бинарный флаг isBusiness
                                        "GuestsCount",       #  дубликат есть точные AdultCount и ChildCount  
                                        "Status_out"], errors="ignore") # утечка данных из будущего для модели 
    
    
    
   # Удаляем строки с техническим кодом PO
    dataframe = dataframe[dataframe['RoomTypeCode'] != 'PO']
    
    #  Создаем числовой признак "Вместимость номера" (Capacity)
    dataframe["Room_capacity"] = dataframe["RoomTypeCode"].apply(get_capacity)
    
    # 1. Удаляем гарантированный технический мусор и бесплатные брони
    trash_rates = ['PO', 'POT', 'TEST', 'TMK', 'COMPL']
    # перед условием — это оператор НЕ (инверсия)
    dataframe = dataframe[~dataframe['RateCode'].isin(trash_rates)]

# 2. Создаем признак "Завтрак уже включен в тариф"
# Ищет подстроку 'BI' в названии тарифа (в любом регистре)
    dataframe['Is_Breakfast_Included'] = dataframe['RateCode'].apply(
        lambda x: 1 if 'BI' in str(x).upper() else 0
    )
    
    # 3. Извлекаем размер скидки из тарифов RACK (если цифр нет, скидка 0)
    dataframe['Rack_Discount_Percent'] = dataframe['RateCode'].apply(get_rack_discount)
    
    
    # Сохраняем таблицу в файл csv
    #dataframe.to_csv(csv_path, index=False, sep=';', encoding='utf-8-sig')

    return dataframe
    

# Создаем датасет для предсказания заказа услуг фитнеса
def prepare_fitness_prediction_data(dataframe):
    # 1. Фильтруем строки: оставляем только тех, кто НЕ отменил и приехал
    df_fitness = dataframe[(dataframe['Status_cancel'] == 0) & (dataframe['Status_noshow'] == 0)].copy()
    
    # Маркируем премиум-сегмент (номера с буквой X)
    df_fitness['is_premium_room'] = df_fitness['RoomTypeCode'].str.contains('X', regex=True).astype(int)


# 2. Удаляем столбцы которые не нужны для предсказания услуги фитнеса
    df_fitness = df_fitness.drop(columns=['Status_cancel',
                                          'Status_noshow',
                                          'Breakfast_order',
                                          'RateCode',
                                          "RoomTypeCode",
                                          "Is_Breakfast_Included"])
    

    
    return df_fitness
    




if __name__ == "__main__":    
    file_path = "D:/Admin/Documents/Учеба/Практика/тесты/random_forest_data.csv"   # D:/Admin/Documents/Учеба/Практика/тесты/merged.csv
    df = pd.read_csv(file_path, sep=';')
    df_fitness = prepare_fitness_prediction_data(df)
    save_dataframe_to_csv_file(df_fitness, "D:/Admin/Documents/Учеба/Практика/тесты", "fitness_data.csv")
# Посмотреть уникальные значения в колонке RateCode RoomTypeCode
#print(df["RateCode"].unique())
 
#prepare_rnd_forest_data(df, "D:/Admin/Documents/Учеба/Практика/тесты")   
    
    
    
    
    
    
    
    
    
    