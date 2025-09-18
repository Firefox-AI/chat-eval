## Chatbot evaluation scripts

The following repository can be used to test chatbots' suitability for use as browser assistants. We evaluate responses along the following dimensions:
- **Tool-Call Accuracy:** how well is the model able to call tools? are the calls formatted correctly? are they appropriate to the situation?
- **Browser-Context Awareness:** can the chatbot correctly track which tab is active and respect retrieved history/content?
- **Assistant Usefulness:** can the chatbot ultimately assist the user with the task at hand?
- **Preference Adherence:**: does the chatbot respect the user's given preferences when available?
- **Response Conciseness:**: is the chatbot overly wordy?
- **Knowledge:** is the chatbot able to answer basic knowledge questions without resorting to outside tools (e.g web search?)


### Usage
1. clone the repo
2. ensure necessary API keys are available in the environment (e.g. default environment variable for openAI APIs is `OPENAI_API_KEY`) 
3. `uv sync`
4. Run the script: `uv run python run_eval.py --model <model-provider:model_id>`

### Datasets
The data used in the the [Mozilla HF repo](https://huggingface.co/datasets/Mozilla/chat-eval). It will be downloaded automatically in the `run_eval.py` script, but can also be downloaded directly from the hub.



