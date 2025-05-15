import flet as ft
import aiohttp
import asyncio
import json
import os
import zipfile
import pathlib

# URL для загрузки данных об играх
JSON_URL = "https://raw.githubusercontent.com/mogd-Kali/bazukagames/refs/heads/main/games.json"
# URL для иконки программы
MAIN_ICON_URL = "https://i.postimg.cc/x8s5FfgR/photo-2025-05-14-22-03-13-Photoroom-1.png"

async def main(page: ft.Page):
    # Настройка страницы
    page.title = "FTeam"
    page.theme_mode = ft.ThemeMode.DARK  # Устанавливаем темную тему
    # Установка фиолетовой темы через primary swatch
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.PURPLE_ACCENT_700)

    # Создаем новую цветовую схему
    page.theme.color_scheme = ft.ColorScheme(
        surface=ft.Colors.GREY_900,
        on_surface=ft.Colors.WHITE,
        background=ft.Colors.GREY_900,
        on_background=ft.Colors.WHITE,
    )

    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO  # Включаем автоматическую прокрутку
    page.window_maximized = True  # Открываем на весь экран при запуске

    # Поле для поиска игр
    search_field = ft.TextField(
        hint_text="Поиск по названию или автору",
        expand=True,
    )

    async def search_button_clicked(e):
        await update_games_list(search_field.value)

    # Добавление поля поиска и кнопки на страницу
    page.add(
        ft.Row([
            search_field,
            ft.ElevatedButton("Поиск", on_click=search_button_clicked),
        ])
    )

    # Добавление главной иконки по центру
    page.add(
        ft.Image(
            src=MAIN_ICON_URL,
            width=150,
            height=150,
            fit=ft.ImageFit.CONTAIN,
            # Выравнивание уже по центру страницы задано page.horizontal_alignment
        )
    )

    # Колонка для отображения списка игр
    games_column = ft.Column(
        expand=True,  # Колонка будет расширяться
        scroll=ft.ScrollMode.AUTO,  # Включаем прокрутку для колонки игр
        spacing=15,  # Отступы между элементами
        horizontal_alignment=ft.CrossAxisAlignment.CENTER  # Центрируем карточки игр
    )
    page.add(games_column)

    # Текстовое поле для отображения статуса загрузки/распаковки
    status_text = ft.Text("", size=12, color=ft.Colors.ON_SURFACE)

    # Прогресс бар для отображения процентов скачивания
    progress_bar = ft.ProgressBar(value=0, width=400)
    progress_text = ft.Text("Загрузка: 0%", size=12, color=ft.Colors.ON_SURFACE)

    # Размещаем прогресс бар и текст по центру внизу
    download_indicator = ft.Column(
        [
            progress_text,
            progress_bar,
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        visible=False,  # Скрываем индикатор до начала загрузки
    )
    page.add(status_text, download_indicator)

    # FilePicker для выбора директории сохранения
    file_picker = ft.FilePicker()
    page.overlay.append(file_picker)
    selected_directory = ft.TextField(label="Выбранная папка", read_only=True)
    page.add(selected_directory)

    def update_status(message):
        """Обновляет текст статуса и страницу."""
        status_text.value = message
        page.update()

    async def download_and_process_file(url: str, save_dir: str, update_status):
        """Скачивает файл с отображением прогресса."""
        try:
            # Получаем имя файла из URL
            filename = url.split('/')[-1]
            # Простая очистка от возможных параметров запроса
            if '?' in filename:
                filename = filename.split('?')[0]

            if not filename:
                filename = "downloaded_file"  # Fallback filename

            save_path = pathlib.Path(save_dir) / filename

            # Показываем индикатор загрузки
            download_indicator.visible = True
            page.update()

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    total_size = int(response.headers.get('Content-Length', 0))

                    downloaded_size = 0
                    chunk_size = 8192

                    with open(save_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(chunk_size):
                            f.write(chunk)
                            downloaded_size += len(chunk)

                            # Вычисляем процент загрузки
                            percent_complete = downloaded_size / total_size if total_size > 0 else 0

                            # Обновляем UI
                            progress_bar.value = percent_complete
                            progress_text.value = f"Загрузка: {percent_complete * 100:.1f}%"
                            page.update()

            update_status(f"Скачивание '{filename}' завершено.")
            progress_text.value = f"Загрузка завершена."  # Устанавливаем статус завершения
            progress_bar.value = 1  # Заполняем прогресс бар полностью
            page.update()  # Обновляем UI после завершения
        except aiohttp.ClientError as e:
            update_status(f"Ошибка скачивания: {e}")
            progress_text.value = f"Ошибка скачивания: {e}"
            page.update()
        except Exception as e:
            update_status(f"Произошла непредвиденная ошибка: {e}")
            progress_text.value = f"Произошла непредвиденная ошибка: {e}"
            page.update()
        finally:
            # Очищаем прогресс бар и текст через некоторое время
            await asyncio.sleep(3)
            download_indicator.visible = False  # Скрываем индикатор
            progress_bar.value = 0
            progress_text.value = ""
            page.update()

    async def on_download_click(e, game_link: str):
        """Обработчик нажатия кнопки скачать."""
        if not game_link:
            update_status("Ссылка для скачивания отсутствует.")
            return

        update_status("Выбор директории для сохранения...")

        def get_directory_result(e: ft.FilePickerResultEvent):
            if e.path:
                selected_directory.value = e.path
                update_status(f"Выбрана директория: {e.path}")
                page.loop.create_task(download_and_process_file(game_link, e.path, update_status))
            else:
                update_status("Выбор директории отменен.")
                selected_directory.value = ""  # Очищаем поле ввода
            page.update()
        file_picker.on_result = get_directory_result

        # Открываем диалог выбора директории
        file_picker.get_directory_path(dialog_title="Выберите папку для сохранения")
        page.update()

    def open_image_dialog(image_src):
        """Открывает диалог с увеличенным изображением."""
        if image_src:
            # Устанавливаем содержимое диалога - картинку
            image_dialog.content = ft.Image(
                src=image_src,
                fit=ft.ImageFit.CONTAIN,  # Картинка будет масштабироваться, сохраняя пропорции
                expand=True  # Картинка займет все доступное пространство диалога
            )
            image_dialog.open = True  # Открываем диалог
            page.update()
        else:
            print("Нет URL изображения для открытия.")  # Логируем, если нет ссылки

    # Helper function to set photo container visibility on hover
    def set_photos_visibility(container, is_hovering_str):
        """Устанавливает видимость контейнера с фото при наведении."""
        # e.data приходит как строка 'true' или 'false'
        is_hovering = is_hovering_str == 'true'
        # Обновляем только если видимость действительно изменилась
        if container.visible != is_hovering:
            container.visible = is_hovering
            page.update()

    async def load_games_data(update_status):
        """Загружает данные об играх с использованием aiohttp."""
        update_status("Загрузка данных об играх...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(JSON_URL) as response:
                    response.raise_for_status()  # Проверка на ошибки HTTP
                    # Читаем ответ как текст и парсим JSON вручную
                    text = await response.text()
                    games_data = json.loads(text)

            if not isinstance(games_data, list):
                update_status("Ошибка: Неверный формат данных. Ожидался список игр.")
                return

            if not games_data:
                update_status("Список игр пуст.")
                return

            update_status("")  # Очистка статуса после успешной загрузки
            return games_data

        except aiohttp.ClientError as e:
            error_message = f"Ошибка загрузки данных с {JSON_URL}: {e}"
            update_status(error_message)
            print(error_message)  # Выводим ошибку в консоль для отладки
            # Опционально: добавить текстовый элемент с ошибкой на страницу
            games_column.controls.append(ft.Text(error_message, color=ft.Colors.RED))
            page.update()
            return []
        except json.JSONDecodeError:
            error_message = f"Ошибка парсинга JSON с {JSON_URL}. Проверьте формат файла."
            update_status(error_message)
            print(error_message)
            games_column.controls.append(ft.Text(error_message, color=ft.Colors.RED))
            page.update()
            return []
        except Exception as e:
            error_message = f"Произошла непредвиденная ошибка при обработке игр: {e}"
            update_status(error_message)
            print(error_message)
            games_column.controls.append(ft.Text(error_message, color=ft.Colors.RED))
            page.update()
            return []

    async def update_games_list(search_term=""):
        """Обновляет список игр в соответствии с поисковым запросом."""
        games_column.controls.clear()  # Очищаем текущий список игр
        page.update()

        filtered_games = []
        if search_term:
            search_term = search_term.lower()
            filtered_games = [
                game for game in all_games_data
                if search_term in game.get('Name', '').lower() or search_term in game.get('Author', '').lower()
            ]
        else:
            filtered_games = all_games_data

        for game in filtered_games:
            # Создаем элементы изображений для photo1 и photo2
            # Они будут видимы, только если есть URL
            photo1_img = ft.GestureDetector(  # Используем GestureDetector
                mouse_cursor=ft.MouseCursor.CLICK,  # Меняем курсор при наведении
                on_tap=lambda e, src=game.get('Photo1'): open_image_dialog(src) if src else None,
                content=ft.Image(  # Оборачиваем Image в GestureDetector
                    src=game.get('Photo1', ''),
                    width=200,  # Примерный размер для превью
                    height=150,  # Примерный размер для превью
                    fit=ft.ImageFit.COVER,  # Как изображение вписывается в размер
                    visible=bool(game.get('Photo1')),  # Видимо, только если есть URL
                )
            )
            photo2_img = ft.GestureDetector(  # Используем GestureDetector
                mouse_cursor=ft.MouseCursor.CLICK,  # Меняем курсор при наведении
                on_tap=lambda e, src=game.get('Photo2'): open_image_dialog(src) if src else None,
                content=ft.Image(  # Оборачиваем Image в GestureDetector
                    src=game.get('Photo2', ''),
                    width=200,  # Примерный размер для превью
                    height=150,  # Примерный размер для превью
                    fit=ft.ImageFit.COVER,  # Как изображение вписывается в размер
                    visible=bool(game.get('Photo2')),  # Видимо, только если есть URL
                )
            )

            # Колонка для размещения photo1 и photo2 (изначально скрыта)
            # photo2 сверху, photo1 снизу
            photos_container = ft.Column(
                controls=[
                    # Добавляем надпись "Скриншоты" если есть хоть одно фото
                    ft.Text("Скриншоты:", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
                    if (bool(game.get('Photo1')) or bool(game.get('Photo2'))) else ft.Container(),
                    photo2_img,  # Фото 2 сверху
                    photo1_img,  # Фото 1 снизу
                ],
                spacing=5,
                visible=False,  # Изначально делаем контейнер невидимым
                horizontal_alignment=ft.CrossAxisAlignment.CENTER  # Центрируем фотографии
            )

            # Контент карточки игры - размещаем элементы по вертикали
            game_content = ft.Column(
                [
                    # Строка с иконкой и названием/автором
                    ft.Row(
                        [
                            ft.Image(src=game.get('Icon', ''), width=60, height=60, fit=ft.ImageFit.CONTAIN),
                            ft.Column(
                                [
                                    ft.Text(
                                        game.get('Name', 'Без названия'),
                                        weight=ft.FontWeight.BOLD,
                                        size=16,
                                        color=page.theme.primary_color  # Цвет берется из темы
                                    ),
                                    ft.Text(
                                        f"Автор: {game.get('Author', 'Неизвестен')}",
                                        size=12,
                                        color=ft.Colors.ON_SURFACE_VARIANT
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                            )
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    # Описание игры
                    ft.Text(
                        game.get('Description', 'Нет описания.'),
                        size=13,
                        color=ft.Colors.ON_SURFACE
                    ),
                    # Добавляем контейнер с фотографиями, который будет скрываться/показываться
                    photos_container,
                    # Кнопка Скачать
                    ft.ElevatedButton(
                        text="Скачать \u2193",  # Unicode символ для иконки "скачать"
                        on_click=lambda e, link=game.get('Link'): page.loop.create_task(
                            on_download_click(e, link)) if link else None
                    ),
                ],
                spacing=10,  # Отступ между элементами в колонке карточки
            )

            # Создаем карточку, оборачивая контент в контейнер для обработки наведения
            game_card = ft.Card(
                elevation=4,
                content=ft.Container(
                    padding=ft.padding.all(15),
                    # width=550, # Можно задать максимальную ширину карточки, но для full screen лучше не задавать
                    border_radius=ft.border_radius.all(10),
                    content=game_content,  # Основное содержимое карточки
                    # Обработчик наведения мыши на контейнер карточки
                    on_hover=lambda e, pc=photos_container: set_photos_visibility(pc, e.data),
                    # Передаем ссылку на контейнер с фото и данные о событии
                    ink=True  # Добавляет эффект чернил при клике (хотя клик по карточке не обрабатывается здесь)
                )
            )
            games_column.controls.append(game_card)
        page.update()  # Обновляем страницу после добавления всех карточек

    # Загружаем данные об играх
    all_games_data = await load_games_data(update_status)
    # Отображаем все игры при запуске
    await update_games_list()

# Запуск приложения Flet
if __name__ == "__main__":
    ft.app(target=main)
