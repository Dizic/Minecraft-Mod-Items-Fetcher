import requests
import json
import os
import logging
import time
from urllib.parse import quote, unquote, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('mod_items.log'),
        logging.StreamHandler()
    ]
)

# Конфигурация
MAX_WORKERS = 10
DELAY_BETWEEN_REQUESTS = 1  # секунды

class ModItemsFetcher:
    def __init__(self, download_images=False):
        self.api_base = "https://minecraft.fandom.com/api.php"
        self.json_file = "mod_items_data.json"
        self.download_images = download_images
        self.images_dir = "mod_items_data"
        if download_images and not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)
        self.load_existing_data()
        self.processed_count = 0
        self.total_count = 0
        self.failed_count = 0
        
    def load_existing_data(self):
        """Загружает существующие данные из JSON файла"""
        try:
            if os.path.exists(self.json_file):
                with open(self.json_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            else:
                self.data = {'mods': []}
        except Exception as e:
            logging.error(f"Ошибка при загрузке данных: {e}")
            self.data = {'mods': []}

    def save_data(self):
        """Сохраняет данные в JSON файл"""
        try:
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            logging.info(f"Данные сохранены в {self.json_file}")
        except Exception as e:
            logging.error(f"Ошибка при сохранении данных: {e}")

    def sanitize_filename(self, filename):
        """Очищает имя файла от недопустимых символов"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename[:255]

    def download_image(self, url, item_name):
        """Скачивает изображение и возвращает локальный путь"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Получаем расширение файла из URL
            parsed_url = urlparse(url)
            path = parsed_url.path
            extension = os.path.splitext(path)[1]
            if not extension:
                extension = '.png'
                
            # Создаем безопасное имя файла
            safe_name = self.sanitize_filename(f"{item_name}_{hash(url)}{extension}")
            filepath = os.path.join(self.images_dir, safe_name)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
                
            logging.info(f"Скачано изображение: {safe_name}")
            return filepath
            
        except Exception as e:
            logging.error(f"Ошибка при скачивании {url}: {e}")
            return ""

    def get_mod_items(self, mod_name):
        """Получает список предметов для конкретного мода"""
        search_query = f"{mod_name} items"
        
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'srsearch': search_query,
            'srnamespace': '0',
            'srlimit': '50'
        }
        
        try:
            response = requests.get(self.api_base, params=params)
            data = response.json()
            
            if 'query' in data and 'search' in data['query']:
                return data['query']['search']
            
        except Exception as e:
            logging.error(f"Ошибка при поиске предметов мода {mod_name}: {e}")
            
        return []

    def get_item_details(self, page_title):
        """Получает детальную информацию о предмете"""
        params = {
            'action': 'query',
            'format': 'json',
            'prop': 'images|extracts',
            'titles': page_title,
            'exintro': True,
            'explaintext': True
        }
        
        try:
            response = requests.get(self.api_base, params=params)
            data = response.json()
            
            pages = data['query']['pages']
            for page_id in pages:
                page = pages[page_id]
                return {
                    'title': page.get('title', ''),
                    'description': page.get('extract', ''),
                    'images': [img['title'] for img in page.get('images', [])] if 'images' in page else []
                }
                
        except Exception as e:
            logging.error(f"Ошибка при получении деталей для {page_title}: {e}")
            
        return None

    def get_image_url(self, image_title):
        """Получает URL изображения"""
        params = {
            'action': 'query',
            'format': 'json',
            'prop': 'imageinfo',
            'iiprop': 'url',
            'titles': image_title
        }
        
        try:
            response = requests.get(self.api_base, params=params)
            data = response.json()
            
            pages = data['query']['pages']
            for page_id in pages:
                if 'imageinfo' in pages[page_id]:
                    return pages[page_id]['imageinfo'][0]['url']
                    
        except Exception as e:
            logging.error(f"Ошибка при получении URL изображения для {image_title}: {e}")
            
        return None

    def process_mod(self, mod_name):
        """Обрабатывает мод и собирает информацию о его предметах"""
        try:
            logging.info(f"Обработка мода: {mod_name}")
            
            # Проверяем, есть ли уже данные для этого мода
            existing_mod = next((mod for mod in self.data['mods'] if mod['mod_name'] == mod_name), None)
            if existing_mod:
                logging.info(f"Мод {mod_name} уже существует в данных")
                return True

            items = self.get_mod_items(mod_name)
            if not items:
                logging.warning(f"Не найдены предметы для мода {mod_name}")
                self.failed_count += 1
                return False

            mod_data = {
                'mod_name': mod_name,
                'items': []
            }
            
            # Многопоточная обработка предметов
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_item = {
                    executor.submit(self.get_item_details, item['title']): item 
                    for item in items
                }
                
                for future in as_completed(future_to_item):
                    item_details = future.result()
                    if item_details:
                        item_data = {
                            'images': []
                        }
                        
                        # Обработка изображений
                        image_futures = []
                        for image_title in item_details['images']:
                            if any(ext in image_title.lower() for ext in ['.png', '.jpg', '.gif']):
                                image_futures.append(
                                    executor.submit(self.process_image, image_title, item_details)
                                )
                        
                        # Собираем результаты обработки изображений
                        for future in as_completed(image_futures):
                            image_data = future.result()
                            if image_data:
                                item_data['images'].append(image_data)
                        
                        if item_data['images']:
                            mod_data['items'].append(item_data)
                            self.processed_count += 1
                            logging.info(f"Обработан предмет: {item_details['title']}")
                    else:
                        self.failed_count += 1

            # Добавляем данные мода в общий список
            self.data['mods'].append(mod_data)
            # Сохраняем обновленные данные
            self.save_data()
            
            time.sleep(DELAY_BETWEEN_REQUESTS)  # Задержка между модами
            return True
            
        except Exception as e:
            logging.error(f"Ошибка при обработке мода {mod_name}: {e}")
            self.failed_count += 1
            return False

    def process_image(self, image_title, item_details):
        """Обрабатывает одно изображение"""
        try:
            image_url = self.get_image_url(image_title)
            if image_url:
                image_data = {
                    'name': item_details['title'],
                    'url': image_url,
                    'localPath': ""
                }
                if self.download_images:
                    local_path = self.download_image(image_url, item_details['title'])
                    image_data['localPath'] = local_path
                return image_data
        except Exception as e:
            logging.error(f"Ошибка при обработке изображения {image_title}: {e}")
        return None

def get_mods_from_json():
    """Получает список модов из mods_data.json"""
    try:
        with open('mods_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [mod['name'] for mod in data]
    except Exception as e:
        logging.error(f"Ошибка при чтении mods_data.json: {e}")
        return []

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Сбор информации о предметах модов Minecraft')
    parser.add_argument('--mods', nargs='+', help='Список модов для обработки')
    parser.add_argument('--download', action='store_true',
                       help='Скачивать изображения')
    parser.add_argument('--from-json', action='store_true',
                       help='Получить список модов из mods_data.json')
    parser.add_argument('--workers', type=int, default=MAX_WORKERS,
                       help=f'Количество потоков (по умолчанию: {MAX_WORKERS})')
    
    args = parser.parse_args()
    
    if args.from_json:
        mods = get_mods_from_json()
        if not mods:
            logging.error("Не удалось получить список модов из mods_data.json")
            return
        logging.info(f"Загружено {len(mods)} модов из mods_data.json")
    elif args.mods:
        mods = args.mods
    else:
        mods = ["AppleSkin"]
    
    fetcher = ModItemsFetcher(download_images=args.download)
    fetcher.total_count = len(mods)
    
    # Многопоточная обработка модов
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(fetcher.process_mod, mod_name) for mod_name in mods]
        
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logging.error(f"Ошибка при обработке мода: {e}")
                fetcher.failed_count += 1

    # Итоговая статистика
    logging.info("\nИтоги:")
    logging.info(f"Всего модов: {fetcher.total_count}")
    logging.info(f"Успешно обработано: {fetcher.processed_count}")
    logging.info(f"Не удалось обработать: {fetcher.failed_count}")

if __name__ == "__main__":
    main() 
