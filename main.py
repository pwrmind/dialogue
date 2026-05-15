import os
import re
import ollama

# Настройки модели Ollama. Замените на вашу (gemma, gemma2, llama3 и т.д.)
MODEL = 'gemma4:e4b-it-q4_K_M'

# Окно живой памяти будет вычисляться динамически: 2 полных раунда
# MEMORY_WINDOW задаётся позже, после выбора участников

def get_available_characters():
    """Сканирует prompts.md и возвращает список всех доступных персонажей (без дубликатов)"""
    if not os.path.exists("prompts.md"):
        print("[Ошибка] Файл prompts.md не найден в текущей директории!")
        return []
    with open("prompts.md", "r", encoding="utf-8") as f:
        content = f.read()
    # Ищем заголовки ## Имя
    characters = re.findall(rf"^##\s+([^\n]+)", content, re.MULTILINE)
    # Удаляем дубликаты, сохраняя порядок
    seen = set()
    unique = []
    for c in characters:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique

def get_character_prompt(name):
    """Извлекает промпт конкретного персонажа из prompts.md"""
    with open("prompts.md", "r", encoding="utf-8") as f:
        content = f.read()
    # Ищем блок от ## Имя до следующего ## или конца файла
    pattern = rf"^## {re.escape(name)}\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
    if match:
        return match.group(1).strip()
    return ""

def parse_dialogue_file():
    """Парсит dialogue.md и возвращает список только реплик персонажей (включая модератора)"""
    if not os.path.exists("dialogue.md"):
        return []
    with open("dialogue.md", "r", encoding="utf-8") as f:
        lines = f.readlines()
    # Фильтруем строки с репликами **Имя**: текст
    return [line.strip() for line in lines if line.strip().startswith("**")]

def get_last_speaker():
    """Возвращает имя последнего, кто оставил реплику в dialogue.md"""
    replies = parse_dialogue_file()
    if not replies:
        return None
    last_line = replies[-1]
    match = re.match(r"\*\*([^*]+)\*\*:", last_line)
    return match.group(1) if match else None

def generate_summary(text_to_summarize):
    """Использует Ollama для создания краткой выжимки старой части диалога"""
    if not text_to_summarize:
        return ""
    prompt = (
        f"Сделай очень краткую выжимку (буквально 2-3 предложения) следующей части спора исторических личностей. "
        f"Выдели только суть их разногласий и главные тезисы. Напиши на русском языке.\n\n"
        f"Текст для сжатия:\n{text_to_summarize}"
    )
    try:
        response = ollama.generate(model=MODEL, prompt=prompt, options={'temperature': 0.3})
        return response['response'].strip()
    except Exception as e:
        print(f"[Предупреждение] Не удалось создать саммари: {e}")
        return ""

def process_context(memory_window):
    """Разделяет историю на 'живую память' и 'хвост' для саммаризации"""
    all_replies = parse_dialogue_file()
    if len(all_replies) <= memory_window:
        return "", "\n".join(all_replies)
    tail_replies = all_replies[:-memory_window]
    live_replies = all_replies[-memory_window:]
    text_for_summary = "\n".join(tail_replies)
    live_context = "\n".join(live_replies)
    print(f"⚙️  Сжимаю старый контекст ({len(tail_replies)} реплик)...")
    summary = generate_summary(text_for_summary)
    return summary, live_context

def generate_reply(speaker, target, topic, memory_window):
    """Генерирует реплику персонажа с учетом сжатого контекста"""
    system_role = get_character_prompt(speaker)
    summary, live_context = process_context(memory_window)

    # Строим адаптивный промпт с акцентом на конструктивный диалог
    context_instruction = ""
    if summary:
        context_instruction += f"Краткое содержание предыдущей части беседы:\n{summary}\n\n"
    if live_context:
        context_instruction += f"Последние реплики диалога (живой контекст):\n{live_context}\n\n"
    else:
        context_instruction += "Диалог только начинается.\n\n"

    full_prompt = (
        f"{system_role}\n\n"
        f"Ты участвуешь в круглом столе на тему: «{topic}».\n"
        f"Твоя задача – не просто высказать свою позицию, а развивать обсуждение.\n"
        f"Ты можешь:\n"
        f"- согласиться с предыдущим оратором, добавив свой аргумент;\n"
        f"- возразить (с уважением и фактами);\n"
        f"- задать уточняющий вопрос;\n"
        f"- предложить синтез двух противоположных идей;\n"
        f"- повернуть разговор к новому аспекту темы.\n"
        f"Избегай повторять одни и те же мысли. Старайся, чтобы диалог двигался вперёд.\n\n"
        f"{context_instruction}\n"
        f"Сейчас твоя очередь. Ты обращаешься к {target} (или комментируешь его/её слова). "
        f"Напиши ОДНУ реплику от имени {speaker}, сохраняя характер, лексику и эпоху.\n"
        f"Реплика должна быть содержательной (2–4 предложения). Не пиши своё имя в начале, не используй кавычки."
    )

    try:
        response = ollama.generate(
            model=MODEL,
            prompt=full_prompt,
            options={
                'temperature': 0.8,
                'top_p': 0.9,
                'repeat_penalty': 1.1
            }
        )
        reply = response['response'].strip()
        # Очистка от артефактов
        reply = reply.lstrip('"').rstrip('"')
        reply = re.sub(rf"^{speaker}:\s*", "", reply, flags=re.IGNORECASE)
        # Запись в markdown-файл
        with open("dialogue.md", "a", encoding="utf-8") as f:
            f.write(f"\n\n**{speaker}**: {reply}")
        print(f"✅ {speaker} добавил реплику в книгу.")
        return reply
    except Exception as e:
        print(f"❌ Ошибка генерации для {speaker}: {e}")
        return ""

def main():
    available = get_available_characters()
    if not available:
        return

    print("=== НАСТРОЙКА ИСТОРИЧЕСКОГО ДИАЛОГА (С САММАРИЗАЦИЕЙ) ===")
    print("Доступные персонажи:")
    for idx, name in enumerate(available, 1):
        print(f"  {idx}. {name}")

    choices = input("\nВведите номера участников через запятую (например: 1,4,5,11): ")
    try:
        selected_indices = [int(i.strip()) - 1 for i in choices.split(",")]
        # Фильтруем дубликаты, сохраняя порядок первого вхождения
        seen = set()
        selected_characters = []
        for idx in selected_indices:
            if 0 <= idx < len(available):
                name = available[idx]
                if name not in seen:
                    seen.add(name)
                    selected_characters.append(name)
    except ValueError:
        print("Неверный ввод. Выбраны первые 3 персонажа.")
        selected_characters = available[:3]

    if len(selected_characters) < 2:
        print("Ошибка: Для диалога необходимо минимум 2 участника.")
        return

    print(f"\nВыбранный состав: {', '.join(selected_characters)}")

    topic = input("\nВведите тему обсуждения (или Enter для темы по умолчанию): ")
    if not topic.strip():
        topic = "Искусственный интеллект: заменит ли машина творческий потенциал человека?"

    try:
        rounds = int(input("Сколько раундов обсуждения провести? (например, 3): ") or "3")
    except ValueError:
        rounds = 3

    # Вычисляем окно живой памяти: 2 полных раунда (каждый раунд = все участники)
    memory_window = len(selected_characters) * 2
    print(f"📌 Окно живой памяти: {memory_window} реплик (последние {len(selected_characters)*2} сообщений)")

    # Пересоздаём чистый файл для новой сессии
    with open("dialogue.md", "w", encoding="utf-8") as f:
        f.write(f"# Круглый стол исторических личностей\n\n")
        f.write(f"**Состав участников**: {', '.join(selected_characters)}\n")
        f.write(f"**Тема**: {topic}\n\n")
        f.write(f"**Модератор**: Приветствую вас, господа. Наша тема сегодня: «{topic}». Прошу высказаться.\n")

    print("\n[Инфо] Файл dialogue.md готов. Запуск симуляции...\n")

    # Симуляция ходов
    last_speaker_name = "Модератор"
    for r in range(rounds):
        print(f"\n--- Раунд {r + 1} из {rounds} ---")
        for speaker in selected_characters:
            # Каждый участник отвечает последнему говорившему
            target = last_speaker_name
            generate_reply(speaker, target, topic, memory_window)
            last_speaker_name = speaker
        # После каждого полного раунда небольшая пауза для читаемости (опционально)
        print(f"  [Раунд {r+1} завершён]")

    print("\n🎉 Беседа завершена! Все реплики и структура сохранены в dialogue.md.")

if __name__ == "__main__":
    main()