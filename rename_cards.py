from pathlib import Path
import shutil

SOURCE_DIR = Path("downloaded_cards")
TARGET_DIR = Path("cards")
TARGET_DIR.mkdir(exist_ok=True)

mapping = {
    "c01.jpg": "Туз Кубков.jpg",
    "c02.jpg": "Двойка Кубков.jpg",
    "c03.jpg": "Тройка Кубков.jpg",
    "c04.jpg": "Четверка Кубков.jpg",
    "c05.jpg": "Пятерка Кубков.jpg",
    "c06.jpg": "Шестерка Кубков.jpg",
    "c07.jpg": "Семерка Кубков.jpg",
    "c08.jpg": "Восьмерка Кубков.jpg",
    "c09.jpg": "Девятка Кубков.jpg",
    "c10.jpg": "Десятка Кубков.jpg",
    "c11.jpg": "Паж Кубков.jpg",
    "c12.jpg": "Рыцарь Кубков.jpg",
    "c13.jpg": "Королева Кубков.jpg",
    "c14.jpg": "Король Кубков.jpg",

    "m00.jpg": "Шут.jpg",
    "m01.jpg": "Маг.jpg",
    "m02.jpg": "Верховная Жрица.jpg",
    "m03.jpg": "Императрица.jpg",
    "m04.jpg": "Император.jpg",
    "m05.jpg": "Иерофант.jpg",
    "m06.jpg": "Влюбленные.jpg",
    "m07.jpg": "Колесница.jpg",
    "m08.jpg": "Сила.jpg",
    "m09.jpg": "Отшельник.jpg",
    "m10.jpg": "Колесо Фортуны.jpg",
    "m11.jpg": "Справедливость.jpg",
    "m12.jpg": "Повешенный.jpg",
    "m13.jpg": "Смерть.jpg",
    "m14.jpg": "Умеренность.jpg",
    "m15.jpg": "Дьявол.jpg",
    "m16.jpg": "Башня.jpg",
    "m17.jpg": "Звезда.jpg",
    "m18.jpg": "Луна.jpg",
    "m19.jpg": "Солнце.jpg",
    "m20.jpg": "Суд.jpg",
    "m21.jpg": "Мир.jpg",

    "p01.jpg": "Туз Пентаклей.jpg",
    "p02.jpg": "Двойка Пентаклей.jpg",
    "p03.jpg": "Тройка Пентаклей.jpg",
    "p04.jpg": "Четверка Пентаклей.jpg",
    "p05.jpg": "Пятерка Пентаклей.jpg",
    "p06.jpg": "Шестерка Пентаклей.jpg",
    "p07.jpg": "Семерка Пентаклей.jpg",
    "p08.jpg": "Восьмерка Пентаклей.jpg",
    "p09.jpg": "Девятка Пентаклей.jpg",
    "p10.jpg": "Десятка Пентаклей.jpg",
    "p11.jpg": "Паж Пентаклей.jpg",
    "p12.jpg": "Рыцарь Пентаклей.jpg",
    "p13.jpg": "Королева Пентаклей.jpg",
    "p14.jpg": "Король Пентаклей.jpg",

    "s01.jpg": "Туз Мечей.jpg",
    "s02.jpg": "Двойка Мечей.jpg",
    "s03.jpg": "Тройка Мечей.jpg",
    "s04.jpg": "Четверка Мечей.jpg",
    "s05.jpg": "Пятерка Мечей.jpg",
    "s06.jpg": "Шестерка Мечей.jpg",
    "s07.jpg": "Семерка Мечей.jpg",
    "s08.jpg": "Восьмерка Мечей.jpg",
    "s09.jpg": "Девятка Мечей.jpg",
    "s10.jpg": "Десятка Мечей.jpg",
    "s11.jpg": "Паж Мечей.jpg",
    "s12.jpg": "Рыцарь Мечей.jpg",
    "s13.jpg": "Королева Мечей.jpg",
    "s14.jpg": "Король Мечей.jpg",

    "w01.jpg": "Туз Жезлов.jpg",
    "w02.jpg": "Двойка Жезлов.jpg",
    "w03.jpg": "Тройка Жезлов.jpg",
    "w04.jpg": "Четверка Жезлов.jpg",
    "w05.jpg": "Пятерка Жезлов.jpg",
    "w06.jpg": "Шестерка Жезлов.jpg",
    "w07.jpg": "Семерка Жезлов.jpg",
    "w08.jpg": "Восьмерка Жезлов.jpg",
    "w09.jpg": "Девятка Жезлов.jpg",
    "w10.jpg": "Десятка Жезлов.jpg",
    "w11.jpg": "Паж Жезлов.jpg",
    "w12.jpg": "Рыцарь Жезлов.jpg",
    "w13.jpg": "Королева Жезлов.jpg",
    "w14.jpg": "Король Жезлов.jpg",
}

missing = []
copied = 0

for src_name, dst_name in mapping.items():
    src = SOURCE_DIR / src_name
    dst = TARGET_DIR / dst_name

    if src.exists():
        shutil.copy2(src, dst)
        copied += 1
    else:
        missing.append(src_name)

print(f"Скопировано: {copied}")
if missing:
    print("Не найдены:")
    for name in missing:
        print(" -", name)
else:
    print("Все 78 карт успешно скопированы.")