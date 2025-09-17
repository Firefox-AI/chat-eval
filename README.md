## Chatbot evaluation scripts

The following repository can be used to test chatbots' suitability as browser assistants along the following lines:
- **Tool-Call Accuracy:** how well is the model able to call tools? are the calls formatted correctly? are they appropriate to the situation?
- **Browser-Context Awareness:** can the chatbot correctly track which tab is active and respect retrieved history/content?
- **Assistant Usefulness:** can the chatbot ultimately assist the user with the task at hand?
- **Preference Adherence:**: does the chatbot respect the user's given preferences?
- **Response Conciseness:**: is the chatbot overly wordy?
- **Knowledge:** is the chatbot able to answer basic knowledge questions without resorting to outside tools (e.g websearch?)


### Usage
1. clone the repo
2. `uv sync`
3. Run the script: `uv run python run_eval.py --model <model-provider:model_id>`

### Datasets
The data used in the the Mozilla HF repo here. It is downloaded automatically in the `run_eval.py` script, but can also be downloaded directly from the hub.


