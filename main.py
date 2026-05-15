import os
import re
import ollama
from collections import defaultdict

# Настройки модели Ollama
MODEL = 'gemma4:e4b-it-q4_K_M'

# Глобальные переменные для отслеживания повторений
character_history = defaultdict(list)  # {имя: [последние реплики]}

def get_available_characters():
    """Сканирует prompts.md и возвращает список уникальных персонажей"""
    if not os.path.exists("prompts.md"):
        print("[Ошибка] Файл prompts.md не найден!")
        return []
    with open("prompts.md", "r", encoding="utf-8") as f:
        content = f.read()
    characters = re.findall(r"^##\s+([^\n]+)", content, re.MULTILINE)
    seen = set()
    unique = []
    for c in characters:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique

def get_character_prompt(name):
    """Извлекает промпт персонажа из prompts.md"""
    with open("prompts.md", "r", encoding="utf-8") as f:
        content = f.read()
    pattern = rf"^## {re.escape(name)}\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
    if match:
        return match.group(1).strip()
    return ""

def parse_dialogue_file():
    """Возвращает список всех реплик (строки, начинающиеся с **)"""
    if not os.path.exists("dialogue.md"):
        return []
    with open("dialogue.md", "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [line.strip() for line in lines if line.strip().startswith("**")]

def get_last_speaker():
    """Возвращает имя последнего говорившего"""
    replies = parse_dialogue_file()
    if not replies:
        return None
    last_line = replies[-1]
    match = re.match(r"\*\*([^*]+)\*\*:", last_line)
    return match.group(1) if match else None

def get_character_last_replies(name, limit=2):
    """Возвращает последние limit реплик данного персонажа"""
    replies = parse_dialogue_file()
    own = [r for r in replies if r.startswith(f"**{name}**")]
    return own[-limit:] if own else []

def generate_summary(text_to_summarize):
    """Создаёт краткую выжимку старого контекста"""
    if not text_to_summarize:
        return ""
    prompt = (
        f"Сделай очень краткую выжимку (2-3 предложения) предыдущей части дискуссии. "
        f"Выдели основные тезисы и разногласия. Напиши на русском языке.\n\n{text_to_summarize}"
    )
    try:
        response = ollama.generate(model=MODEL, prompt=prompt, options={'temperature': 0.3})
        return response['response'].strip()
    except Exception as e:
        print(f"[Предупреждение] Ошибка саммари: {e}")
        return ""

def process_context(memory_window):
    """Разделяет историю на 'живую память' и сжимаемый хвост"""
    all_replies = parse_dialogue_file()
    if len(all_replies) <= memory_window:
        return "", "\n".join(all_replies)
    tail = all_replies[:-memory_window]
    live = all_replies[-memory_window:]
    print(f"⚙️ Сжимаю {len(tail)} старых реплик...")
    summary = generate_summary("\n".join(tail))
    return summary, "\n".join(live)

def generate_reply(speaker, target, topic, memory_window, round_num):
    """Генерирует реплику с жёсткой структурой и контролем повторов"""
    system_role = get_character_prompt(speaker)
    summary, live_context = process_context(memory_window)
    own_history = get_character_last_replies(speaker, limit=2)
    
    # Блок запрета повторов
    repeat_warning = ""
    if own_history:
        repeat_warning = f"\n⚠️ Ты уже говорил:\n{chr(10).join(own_history)}\nНе повторяй эти мысли. Предложи новое развитие или синтез.\n"
    
    context = ""
    if summary:
        context += f"Краткое содержание предыдущей части:\n{summary}\n\n"
    if live_context:
        context += f"Последние реплики:\n{live_context}\n\n"
    if repeat_warning:
        context += repeat_warning
    
    full_prompt = (
        f"{system_role}\n\n"
        f"Тема круглого стола: «{topic}».\n"
        f"Ты отвечаешь {target}.\n\n"
        f"Твоя реплика должна строго соответствовать теме и состоять из четырёх частей:\n"
        f"1. **Реакция**: согласись или не согласись с предыдущим оратором (если это первый ход – просто представь позицию).\n"
        f"2. **Новая идея**: введи конкретный пример, метафору, контраргумент или решение, связанное с темой. Не повторяй общих фраз.\n"
        f"3. **Развитие**: покажи, как твоя идея связана с тем, что сказал {target}, и с темой в целом.\n"
        f"4. **Вопрос**: задай вопрос или брось вызов, чтобы диалог продолжился.\n\n"
        f"{context}\n"
        f"Напиши ОДНУ реплику от имени {speaker} (2-4 предложения). Не пиши своё имя в начале, не используй кавычки. "
        f"Избегай абстрактных лекций – будь конкретен и привязан к теме «{topic}»."
    )
    
    try:
        response = ollama.generate(
            model=MODEL,
            prompt=full_prompt,
            options={'temperature': 0.85, 'top_p': 0.9, 'repeat_penalty': 1.15}
        )
        reply = response['response'].strip()
        reply = reply.lstrip('"').rstrip('"')
        reply = re.sub(rf"^{speaker}:\s*", "", reply, flags=re.IGNORECASE)
        
        # Запись в файл
        with open("dialogue.md", "a", encoding="utf-8") as f:
            f.write(f"\n\n**{speaker}**: {reply}")
        print(f"✅ {speaker} ответил {target}")
        
        # Сохраняем в историю для контроля повторов
        character_history[speaker].append(reply)
        if len(character_history[speaker]) > 3:
            character_history[speaker].pop(0)
        
        return reply
    except Exception as e:
        print(f"❌ Ошибка генерации {speaker}: {e}")
        return ""

def generate_moderator(topic, round_num):
    """Генерирует промежуточную реплику модератора"""
    prompt = (
        f"Ты – модератор круглого стола на тему «{topic}». "
        f"Дискуссия идёт {round_num} раундов. Твоя задача:\n"
        f"- Кратко подвести итог того, что уже обсудили (не перечисляй, а выдели главное противоречие).\n"
        f"- Задать новый, более конкретный подвопрос, чтобы разговор не топтался на месте.\n"
        f"- Напомнить участникам, что они должны привязываться к теме «{topic}».\n\n"
        f"Напиши ОДНУ реплику модератора (2-3 предложения). Обращайся ко всем участникам."
    )
    try:
        response = ollama.generate(model=MODEL, prompt=prompt, options={'temperature': 0.7})
        reply = response['response'].strip()
        with open("dialogue.md", "a", encoding="utf-8") as f:
            f.write(f"\n\n**Модератор**: {reply}")
        print("  📢 Модератор подвёл итог и задал новый вопрос")
    except Exception as e:
        print(f"❌ Ошибка модератора: {e}")

def main():
    available = get_available_characters()
    if not available:
        return
    
    print("=== КРУГЛЫЙ СТОЛ ИСТОРИЧЕСКИХ ЛИЧНОСТЕЙ (ВЕРСИЯ 2.0) ===")
    print("Доступные персонажи:")
    for idx, name in enumerate(available, 1):
        print(f"  {idx}. {name}")
    
    choices = input("\nВведите номера через запятую (например: 1,4,5,11): ")
    try:
        indices = [int(i.strip()) - 1 for i in choices.split(",")]
        seen = set()
        selected = []
        for idx in indices:
            if 0 <= idx < len(available):
                name = available[idx]
                if name not in seen:
                    seen.add(name)
                    selected.append(name)
    except ValueError:
        print("Неверный ввод. Выбраны первые 3.")
        selected = available[:3]
    
    if len(selected) < 2:
        print("Нужно минимум 2 участника.")
        return
    
    print(f"\nСостав: {', '.join(selected)}")
    topic = input("\nТема (Enter для темы по умолчанию): ")
    if not topic.strip():
        topic = "Искусство жить в мире, где оригинал — устаревший миф, а подделка — новая реальность"
    
    try:
        rounds = int(input("Количество раундов (каждый раунд = все участники): ") or "5")
    except ValueError:
        rounds = 5
    
    memory_window = len(selected) * 2  # живая память = 2 полных раунда
    
    # Инициализация файла
    with open("dialogue.md", "w", encoding="utf-8") as f:
        f.write(f"# Круглый стол исторических личностей\n\n")
        f.write(f"**Состав**: {', '.join(selected)}\n")
        f.write(f"**Тема**: {topic}\n\n")
        f.write(f"**Модератор**: Добрый день, господа! Сегодня мы обсуждаем: «{topic}». "
                f"Прошу каждого высказываться по делу, реагировать на предыдущего, предлагать новые идеи и задавать вопросы. "
                f"Начнём!\n")
    
    print("\n[СТАРТ] Генерация диалога...\n")
    last_speaker = "Модератор"
    
    for r in range(rounds):
        print(f"\n--- РАУНД {r+1} из {rounds} ---")
        for speaker in selected:
            generate_reply(speaker, last_speaker, topic, memory_window, r+1)
            last_speaker = speaker
        
        # Модерация после каждого раунда, кроме последнего? Добавим после каждого нечётного (кроме финала)
        if r < rounds - 1 and (r+1) % 2 == 0:
            generate_moderator(topic, r+1)
            last_speaker = "Модератор"  # чтобы следующий ответил модератору
    
    print("\n🎉 Диалог завершён. Результат в dialogue.md")

if __name__ == "__main__":
    main()