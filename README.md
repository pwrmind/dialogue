# 🏛️ Historical Agents Podcast Simulator
Minimalist Python framework for simulating dynamic group discussions and podcasts between historical figures (e.g., Tesla, Ford, Machiavelli, Socrates, Musk) using local LLMs via **Ollama**.

The entire conversation is generated on the fly, managed by a smart token-saving context summarizer, and formatted directly into a beautiful, human-readable **Markdown book/script**.
---## ✨ Features
* **Zero-Cost & Private**: Runs completely locally using `ollama` and lightweight models (like `gemma`, `gemma2`, `llama3`).
* **Esthetically Simple**: Uses plain Markdown files (`prompts.md` and `dialogue.md`) for configuration, history tracking, and final output.* **Smart Hybrid Memory**: Keeps the last $N$ turns as crisp, raw text for a lively flow, while automatically compressing the distant past into a short summary. Prevents LLM context overflow.* **Interactive Lineup**: Choose your speakers and set custom discussion topics directly from the terminal before starting.
---## 🛠️ Tech Stack* **Language**: Python 3.10+
* **LLM Engine**: [Ollama](https://ollama.com)
* **Default Model**: `gemma` (can be changed to any local model)
* **Storage Format**: Markdown (`.md`)
---## 🚀 Quick Start### 1. PrerequisitesMake sure you have **Ollama** installed and running locally. Download your model of choice:```bash
ollama run gemma
```
### 2. InstallationClone this repository and install the official Ollama python dependency:```bash
git clone https://github.com
cd historical-agents-podcast
pip install ollama
```
### 3. Setup FilesEnsure your project directory contains the following three files:
* `main.py` — The core orchestrator script.
* `prompts.md` — System descriptions defining personalities.
* `dialogue.md` — (Auto-generated) The final output script.
### 4. Run the DiscussionLaunch the simulator via terminal:```bash
python main.py
```

Follow the interactive prompts to pick your lineup (e.g., `1,3,5`), set a provocative topic, and specify the number of rounds.
---## 📂 Project Architecture

├── prompts.md # Database of system instructions for each historical character
├── main.py # Script reading prompts, managing turns, handling summaries, calling Ollama
└── dialogue.md # Live-updated, beautifully formatted script of the discussion


### How the Hybrid Memory Works
When the chat length exceeds the `MEMORY_WINDOW` (default: 5), the system automatically splits the history:

[ Beginning of Conversation ] -> Compressed into a 3-sentence summary by LLM
↓
[ Last 5 Live Replies ] -> Passed raw to preserve humor, rhythm, and direct address
↓
[ Target Agent Prompt ] -> Combined with the above to generate the perfect next line


---

## 🎭 Available Characters (Expandable)

Modify or add new personalities inside `prompts.md` using the simple `## Character Name` markdown headers. Out-of-the-box characters include:
* **Inventors & Engineers**: Nikola Tesla, Thomas Edison, Steve Jobs
* **Industrialists & Magnates**: Henry Ford, John D. Rockefeller, Andrew Carnegie, Elon Musk
* **Thinkers & Leaders**: Socrates, Isaac Newton, Niccolo Machiavelli, Karl Marx, Cleopatra, Marie Curie, Albert Einstein, Coco Chanel

---

## 📝 Example Output (`dialogue.md`)

```markdown
# Round Table of Historical Minds

**Lineup**: Nikola Tesla, Thomas Edison, Elon Musk
**Topic**: Is intuitive genius superior to methodical commercial testing?

**Moderator**: Welcome gentlemen. How should humanity approach true innovation?

**Nikola Tesla**: True innovation is a flash of lightning in the mind, capturing the foundational resonance of the cosmos. If you map the wheel perfectly in your thoughts, you do not waste sweat building a thousand broken prototypes.

**Thomas Edison**: Nature doesn't surrender secrets to mere daydreams, Nikola. My factory floor proved that genius is ninety-nine percent perspiration. A patent that cannot be manufactured and sold to improve a common man's life is just ink on paper.

**Elon Musk**: I think you both have a point, but velocity of iteration is what actually beats everything. Tesla has the core physics right—first principles thinking is mandatory. But Edison's vertical integration and production hell are where the real work happens. If you don't build the machine that builds the machine, you're just tweeting into the void.
```

---

## 🤝 Contributing

Feel free to fork this project, add more historic characters to `prompts.md`, or submit PRs to enhance the agent orchestration engine.

