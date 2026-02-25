# Project Context

## Purpose
D4C (Debug for Code) is a research project for LLM-based Automated Program Repair (APR). The project explores a new paradigm for program repair by aligning with LLM's pre-trained objectives (next token prediction) rather than traditional infilling approaches. It focuses on direct debugging of entire programs without requiring statement-level fault localization.

**Key Goals:**
- Demonstrate that objective alignment improves LLM's APR capability
- Replace traditional "localize-then-repair" workflow with direct debugging
- Achieve state-of-the-art results on Defects4J and DebugBench benchmarks
- Provide reproducible research artifacts for the APR community

## Tech Stack
- **Language:** Python 3.10 (core experiments); `ppl/` tooling uses Python >=3.13 via `uv`
- **ML/LLM Framework:** 
  - PyTorch 2.5.1
  - Transformers 4.47.1 (Hugging Face)
  - Accelerate 1.2.1
- **LLM Models:**
  - Remote: OpenAI-compatible chat models (e.g., GPT-4) and DeepSeek (`deepseek-reasoner`) via `utils/chat_remote.py`
  - Local: HuggingFace causal LMs via `utils/chat_local.py` (default: `mistralai/Mixtral-8x7B-Instruct-v0.1`)
- **Embeddings (optional):**
  - Bailian/DashScope-compatible embeddings endpoint (e.g., `text-embedding-v4`) via `RemoteChat.get_embedding()`
- **Data / Infra:**
  - Pandas 1.5.3
  - Pydantic 2.8.2
  - Requests 2.32.3
  - Python-dotenv 1.0.1
  - Tiktoken 0.6.0 (tokenization)
  - Retry 0.9.2 (API resilience)
  - TQDM 4.66.2 (progress bars)
- **Testing/Evaluation:**
  - Defects4J v3.0 (Java bug benchmark)
  - DebugBench (Python bug benchmark via LeetCode)
  - Python-leetcode 1.2.1
  - Gym 0.26.2 (LeetCode submission environment wrapper)
- **Analysis / Clustering (optional):**
  - Matplotlib 3.10.6
  - Scikit-learn 1.8.0
  - cuVS vector search (CUDA12): pylibraft-cu12 24.10.0, cuvs-cu12 24.10.0, rmm-cu12 24.10.0, cupy-cuda12x 13.3.0

## Project Conventions

### Code Style
- **Python Style:** Follow standard Python conventions (PEP 8)
- **File Naming:** 
  - Generator scripts: `d4j_*.py`, `debugbench.py`, `defects4j.py`
  - Utility modules: `chat_local.py`, `chat_remote.py`, `patch_apply.py`
  - Prompt templates: module-level variables in SCREAMING_SNAKE_CASE
- **Function Naming:** 
  - Main entry points: `debug(args)`
  - Testing functions: `test(...)`
  - Utility functions: snake_case descriptive names
- **Configuration:** YAML files for all configurable parameters (API keys, model settings, timeouts)
- **Prompts:** Stored in `prompt/` directory as Python modules with template strings

### Architecture Patterns
- **Modular Design:**
  - `generator/` - Patch generation logic for different benchmarks
  - `prompt/` - Prompt templates separated by benchmark (Defects4J, DebugBench)
  - `utils/` - Reusable components (chat clients, patch application)
  - `embedding/` - Text embedding + optional GPU vector store (`embedding/vector_index/`) for similarity search/clustering
  - `validator/` - Patch validation logic
  - `dpp/` - Diversity sampling utilities (greedy k-DPP) over clustering results
  - `ppl/` - Perplexity evaluation tooling (separate `uv` environment)
- **Chat Abstraction:**
  - `RemoteChat` class for API-based models (OpenAI, DeepSeek, etc.)
  - `LocalChat` class for local model inference (Mixtral)
  - Unified interface with retry logic for robustness
- **Device Detection:** Automatic device selection (CUDA, MPS for Mac, CPU fallback)
- **Proxy Support:** Multiple API proxy configurations for rate limiting and redundancy
- **Early Stopping:** Optional feature to reduce token costs when valid patch is found

### Testing Strategy
- **Automated Validation:** 
  - Defects4J: JUnit test execution via Defects4J framework
  - DebugBench: LeetCode submission and evaluation
- **Test Execution:**
  - Defects4J tests run during patch generation (optional early stopping)
  - DebugBench tests run via `evaluate.py` script
- **Timeout:** 10-minute default timeout for test execution (`config.yaml:test_config.time_out=600`, configurable)
- **Result Storage:** CSV files in `result/` directory with evaluation metadata
- **Archived Results:** Reference results stored in `archive/` directory with `_archived` suffix

### Git Workflow
- Research project - not explicitly documented in codebase
- Results and logs excluded from version control (stored in `result/`, `log/` directories)
- Large artifacts are gitignored (e.g., `archive/`, `data/`, `defects4j/`, `embedding/vectors/`, `embedding/vector_index/`)
- Configuration uses placeholders (e.g., `xxxxxxxx` for API keys and cookies)

## Domain Context

### Automated Program Repair (APR)
- **Traditional APR:** Requires statement-level fault localization (FL) followed by patch generation
- **D4C Approach:** Direct debugging without FL - processes entire functions/programs
- **Output Alignment:** Generates complete refined functions rather than infilling masked spans
- **Prompt Structure:** Includes buggy code, comments, error messages, and failed test cases

### Benchmarks
1. **Defects4J v3.0:**
   - Java bug benchmark (Chart, Cli, Closure, Lang, Math, Time, etc.)
   - Real bugs from open-source projects
   - Requires Java 11, Perl, SVN, Git
   - V3.0 deprecated some v2.0 bugs (Lang 18/25/48, JacksonDatabind 65/89)

2. **DebugBench:**
   - Python bug benchmark via LeetCode
   - Requires LeetCode account cookies
   - Automated submission and evaluation
   - Rate limiting considerations (use multiple accounts)

### Key Metrics
- **Perfect FL Setting:** Assumes correct buggy location is known
- **Non-Perfect FL:** Uses FLUCCS for method-level fault localization
- **Sampling:** 10 attempts for Defects4J, 3 for DebugBench
- **Success:** Patch passes all JUnit/LeetCode tests

## Important Constraints

### Technical Constraints
- **Platform:** Linux recommended (Defects4J has unexplained bugs on macOS)
- **GPU Requirements:** Local inference requires GPUs capable of running Mixtral 8x7B MoE
- **Memory:** Sufficient GPU memory for Mixtral (8x7B parameters)
- **CUDA Requirements (optional):** cuVS vector store requires an NVIDIA GPU + CUDA 12 runtime
- **Java Version:** Java 11 required for Defects4J
- **Perl Version:** Perl >= 5.0.12 required for Defects4J
- **Python Version:** Python 3.10 (strict requirement)
- **PPL Tooling:** `ppl/` uses `uv` and declares Python >= 3.13 in `ppl/pyproject.toml`
- **Path Assumptions:** Some scripts contain hard-coded absolute paths from the original research environment; update these paths to match your local filesystem layout

### API Constraints
- **Rate Limiting:** LeetCode accounts can be banned with frequent submissions
- **Token Costs:** Defects4J experiments can be expensive (long Java code snippets)
- **Proxy Reliability:** Multiple proxy configurations for resilience
- **Retry Logic:** 3 retries with exponential backoff for API calls

### Research Constraints
- **Reproducibility:** Fixed random seeds, temperature settings
- **Benchmark Compatibility:** Must handle Defects4J version changes
- **Evaluation Fairness:** No testing on MacOS, consistent timeout settings

## External Dependencies

### Core Services
- **OpenAI API:** GPT-4 models for remote inference
- **DeepSeek API:** Alternative LLM provider
- **Bailian/DashScope API:** Embedding endpoint used by `embedding/` module
- **Hugging Face Hub:** Model downloads for Mixtral
- **LeetCode API:** Automated code submission for DebugBench

### Bug Benchmarks
- **Defects4J:** Cloned from GitHub (https://github.com/rjust/defects4j)
- **FLUCCS:** Method-level fault localization tool (BitBucket)

### Development Tools
- **CPAN:** Perl dependency management for Defects4J
- **SVN:** Version control for some Defects4J projects
- **Git:** Version control for project repositories

### Model Checkpoints
- **Mixtral 8x7B Instruct v0.1:** HuggingFace model repository
- Configurable via `cp_path` in `config.yaml` (defaults to HuggingFace cache)

### Proxy Services
- Multiple API proxy endpoints configured in `chat_remote.py`:
  - AI proxy (api.ai-gaochao.cn)
  - OMG proxy (aigptx.top)
  - OpenAI proxies (api.shubiaobiao.cn, api.f2gpt.com)
  - DeepSeek direct API (api.deepseek.com)
  - Bailian/DashScope embeddings endpoint (dashscope.aliyuncs.com)
