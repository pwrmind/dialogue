import os
import re
import ollama

# Настройки модели Ollama. Замените на вашу (gemma, gemma2, llama3 и т.д.)
MODEL = 'gemma4:e4b-it-q4_K_M' 

# Окно живой памяти: сколько последних реплик передавать без изменений
MEMORY_WINDOW = 5 

def get_available_characters():
    """Сканирует prompts.md и возвращает список всех доступных персонажей"""
    if not os.path.exists("prompts.md"):
        print("[Ошибка] Файл prompts.md не найден в текущей директории!")
        return []
    with open("prompts.md", "r", encoding="utf-8") as f:
        content = f.read()
    characters = re.findall(rf"##\s+([^\n]+)", content)
    return [c.strip() for c in characters]

def get_character_prompt(name):
    """Извлекает промпт конкретного персонажа из prompts.md"""
    with open("prompts.md", "r", encoding="utf-8") as f:
        content = f.read()
    pattern = rf"## {name}\n(.*?)(?=\n##|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else ""

def parse_dialogue_file():
    """Парсит dialogue.md и возвращает список только реплик персонажей"""
    if not os.path.exists("dialogue.md"):
        return []
    with open("dialogue.md", "r", encoding="utf-8") as f:
        lines = f.readlines()
    # Фильтруем только строки с репликами в формате **Имя**: текст
    return [line.strip() for line in lines if line.strip().startswith("**")]

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
        response = ollama.generate(model=MODEL, prompt=prompt)
        return response['response'].strip()
    except Exception as e:
        print(f"[Предупреждение] Не удалось создать саммари: {e}")
        return ""

def process_context():
    """Разделяет историю на 'живую память' и 'хвост' для саммаризации"""
    all_replies = parse_dialogue_file()
    
    if len(all_replies) <= MEMORY_WINDOW:
        # Если реплик мало, передаем всё как есть, саммари пустое
        live_context = "\n".join(all_replies)
        return "", live_context

    # Разделяем на живую часть и старую
    tail_replies = all_replies[:-MEMORY_WINDOW]
    live_replies = all_replies[-MEMORY_WINDOW:]
    
    text_for_summary = "\n".join(tail_replies)
    live_context = "\n".join(live_replies)
    
    print(f"⚙️  Сжимаю старый контекст ({len(tail_replies)} реплик)...")
    summary = generate_summary(text_for_summary)
    
    return summary, live_context

def generate_reply(speaker, target_name):
    """Генерирует реплику персонажа с учетом сжатого контекста"""
    system_role = get_character_prompt(speaker)
    summary, live_context = process_context()
    
    # Строим адаптивный промпт
    context_instruction = ""
    if summary:
        context_instruction += f"Краткое содержание предыдущей части беседы:\n{summary}\n\n"
    context_instruction += f"Последние реплики диалога (живой контекст):\n{live_context}"

    full_prompt = (
        f"{system_role}\n\n"
        f"Вы ведите круглый стол. Представь, что ты помнишь суть разговора.\n"
        f"{context_instruction}\n\n"
        f"Задание:\n"
        f"Сейчас твоя очередь. Напиши ОДНУ реплику от своего лица ({speaker}), "
        f"обращаясь к персонажу {target_name} или комментируя последнюю мысль. "
        f"Отвечай строго в своем характере, манере речи и эпохе. Будь лаконичен.\n"
        f"ВАЖНО: Выведи ТОЛЬКО текст своей реплики. Не пиши свое имя в начале, не используй кавычки."
    )

    try:
        response = ollama.generate(model=MODEL, prompt=full_prompt)
        reply = response['response'].strip()
        
        # Защитная очистка текста от артефактов LLM
        reply = reply.lstrip('"').rstrip('"')
        reply = re.sub(rf"^{speaker}:\s*", "", reply, flags=re.IGNORECASE)

        # Запись в markdown-файл
        with open("dialogue.md", "a", encoding="utf-8") as f:
            f.write(f"\n\n**{speaker}**: {reply}")
        
        print(f"✅ {speaker} добавил реплику в книгу.")
    except Exception as e:
        print(f"❌ Ошибка генерации для {speaker}: {e}")

def main():
    available = get_available_characters()
    if not available:
        return

    print("=== НАСТРОЙКА ИСТОРИЧЕСКОГО ДИАЛОГА (С САММАРИЗАЦИЕЙ) ===")
    print("Доступные персонажи:")
    for idx, name in enumerate(available, 1):
        print(f"  {idx}. {name}")
    
    # Выбор участников через консоль
    choices = input("\nВведите номера участников через запятую (например: 1,4,5,11): ")
    try:
        selected_indices = [int(i.strip()) - 1 for i in choices.split(",")]
        selected_characters = [available[i] for i in selected_indices if 0 <= i < len(available)]
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

    # Пересоздаем чистый файл для новой сессии
    with open("dialogue.md", "w", encoding="utf-8") as f:
        f.write(f"# Круглый стол исторических личностей\n\n")
        f.write(f"**Состав участников**: {', '.join(selected_characters)}\n")
        f.write(f"**Тема**: {topic}\n\n")
        f.write(f"**Модератор**: Приветствую вас, господа. Наша тема сегодня: «{topic}». Прошу высказаться.")

    print("\n[Инфо] Файл dialogue.md готов. Запуск симуляции...\n")

    # Симуляция ходов
    for r in range(rounds):
        print(f"\n--- Раунд {r + 1} из {rounds} ---")
        for i, speaker in enumerate(selected_characters):
            # Определяем, к кому обращаться
            if i == 0 and r == 0:
                target = "Модератор"
            elif i == 0:
                target = selected_characters[-1]  # К последнему из прошлого раунда
            else:
                target = selected_characters[i - 1]  # К предыдущему в списке
                
            generate_reply(speaker, target)

    print("\n🎉 Беседа завершена! Все реплики и структура сохранены в dialogue.md.")

if __name__ == "__main__":
    main()
