
import os
from dotenv import load_dotenv
from gigachat import GigaChat
import argparse #argparse — это встроенная библиотека Python для работы с аргументами командной строки.
import re # re — это встроенная библиотека Python для работы с регулярными выражениями, которая позволяет выполнять операции поиска и замены в строках на основе определенных шаблонов.

MAX_INPUT_LENGTH = int(os.getenv("MAX_INPUT_LENGTH") or 12)

def main():
    
    exception_message = f"Пожалуйста, передайте запрос через флаг -i. Например: python copykit.py -i 'Название вашего проекта'"
    
    try:
        parser = argparse.ArgumentParser(description="Передайте свой запрос в гигачат") # Создаем парсер аргументов командной строки он позволяет нам легко обрабатывать аргументы, переданные при запуске скрипта.
        # причисляет аргументам флаги и описания, что позволяет пользователю понять, какие аргументы доступны и как их использовать.

        parser.add_argument("-i", type=str, required=True, help="Введите ваш запрос") #required=True делает аргумент обязательным, и если пользователь не предоставит его при запуске скрипта, будет выведено сообщение об ошибке.
        args = parser.parse_args()

        user_input = args.i

    except SystemExit:
        print(exception_message)
        return

    print(f"User input: {user_input}")

    if validate_input_length(user_input):
        result_snippets = generate_snippets(user_input)
        result_keywords = generate_keywords(user_input)

        print(f"СНИППЕТЫ: {result_snippets}")
        print("\n")
        print(f"КЛЮЧЕВЫЕ СЛОВА: {result_keywords}")
    else:
        raise ValueError(
            f"Длина запроса должна быть не больше {MAX_INPUT_LENGTH} символов и не меньше 3.\n"
            f"Длина вашего запроса: {len(user_input)} символов.\n"
        )

def validate_input_length(promt: str = None):

    if promt is None:
        return False
    
    if len(promt) < 3:
        return False
    
    if len(promt) > MAX_INPUT_LENGTH:
        return False
    
    return True


def generate_snippets(promt: str):

    load_dotenv()
    GIGA_API = os.getenv("GIGA_API")

    if not GIGA_API:
        raise ValueError("Переменная окружения GIGA_API не найдена. Проверь .env файл")

    if " " in GIGA_API or "\n" in GIGA_API:
        raise ValueError("GIGA_API содержит лишние пробелы или переносы строки")

    giga = GigaChat(
        credentials=GIGA_API.strip(),
        verify_ssl_certs=False
    )

    final_prompt = f"""
    Ты сильный бренд-стратег и performance-копирайтер.
    На входе только название проекта или бизнеса: "{promt}".

    Твоя задача: по одному названию собрать основу для продающего описания.
    Если название неоднозначно, выбери наиболее вероятную и безопасную трактовку ниши, но не выдумывай конкретику, которую нельзя уверенно вывести из названия.

    Правила:
    1. Пиши только по-русски.
    2. Не используй клише, канцелярит, абстракции и общие фразы вроде "высокое качество", "индивидуальный подход", "лучшее решение".
    3. Не выдумывай цифры, города, сроки, награды, цены, технологии, лицензии, статистику и другие непроверяемые факты.
    4. Формулировки должны быть конкретными, маркетингово сильными и правдоподобными.
    5. В блоке "доказательства/факты" используй только безопасные и универсальные варианты, если точных фактов из названия не следует: например, "кейсы, отзывы, прозрачный процесс", "портфолио, примеры работ, понятные условия".
    6. Call to action должен быть коротким и действенным: 2-4 слова.
    7. Тон должен быть из 2-3 слов.

    Формат ответа:
    ровно одна строка без переносов;
    только 6 значений через запятую и пробел в таком порядке:
    целевая аудитория, ключевая боль, уникальное обещание, доказательства/факты, call to action, тон.

    Не добавляй подписи, пояснения, кавычки, нумерацию и лишние символы.
    """.strip()

    try:
        response = giga.chat(
            {
                # "model": "GigaChat-Pro",
                "messages": [
                    {
                        "role": "user",
                        "content": final_prompt,
                    }
                ],
                "max_tokens": 100,
            }
        )

        model_response: str = response.choices[0].message.content
        model_response = model_response.strip().replace("\n", " ")

        last_char = model_response[-1]
        if last_char not in [",", ".", ";", "!", "?"]:
            model_response += "..."

        return model_response

    except Exception as e:
        print("Ошибка при запросе к GigaChat:", e)
        raise
    finally:
        giga.close()

def generate_keywords(promt: str) -> list[str]:

    load_dotenv()
    GIGA_API = os.getenv("GIGA_API")

    if not GIGA_API:
        raise ValueError("Переменная окружения GIGA_API не найдена. Проверь .env файл")

    if " " in GIGA_API or "\n" in GIGA_API:
        raise ValueError("GIGA_API содержит лишние пробелы или переносы строки")

    giga = GigaChat(
        credentials=GIGA_API.strip(),
        verify_ssl_certs=False
    )

    final_prompt = f"""
    Ты бренд-стратег, SEO-копирайтер и редактор смыслов.
    На входе только название проекта или бизнеса: "{promt}".

    Сгенерируй 5 релевантных ключевых фраз для этого проекта.
    Если название неоднозначно, выбери наиболее вероятную нишу, но не придумывай узкие детали, которых нет во входных данных.

    Правила:
    1. Пиши только по-русски.
    2. Верни ровно 5 ключевых фраз.
    3. Каждая фраза должна быть естественной для поиска и состоять из 1-3 слов.
    4. Не используй хэштеги, кавычки, нумерацию, аббревиатуры, англицизмы без необходимости и склеенные слова.
    5. Не повторяй одну и ту же мысль разными словами и не дублируй однокоренные фразы.
    6. Избегай слишком общих слов вроде "бизнес", "услуги", "проект", если они не раскрывают суть.
    7. Не добавляй лишний текст, пояснения и служебные пометки.

    Формат ответа:
    ровно одна строка без переносов;
    только 5 фраз через запятую и пробел.
    """.strip()

    try:
        response = giga.chat(
            {
                # "model": "GigaChat-Pro",
                "messages": [
                    {
                        "role": "user",
                        "content": final_prompt,
                    }
                ],
                "max_tokens": 100,
            }
        )

        model_response: str = response.choices[0].message.content
        model_response = model_response.strip().replace("\n", " ")

        cleaned = re.sub(r"[.,;!?]$", "", model_response)
        keywords = [kw.strip() for kw in re.split(r",\s*", cleaned) if kw.strip()] # if kw.strip() проверяет что строка не пустая

        return keywords

    except Exception as e:
        print("Ошибка при запросе к GigaChat:", e)
        raise
        return []
    finally:
        giga.close()

if __name__ == "__main__":
    main()
