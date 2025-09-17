JUDGE_PROMPT="""You are an evaluator for a multi-turn browser assistant system. 
Your job is to evaluate the assistant’s most recent response to the conversation, focusing on tool usage, context tracking, usefulness, preference adherence, conciseness, and knowledge.

You will be given:
- The conversation history (including tool calls and truncated outputs if long) ending with a user query
- The assistant's response to the user query

The assistant system has the following tools in hand:
- @get_page_contents(url): returns the text content of a web page given the url.
- @search_history(search_term): returns the most relevant history items related to search term with each containing url, title, visited time and a description of the page if available.
- @get_preferences(query=""): retrieve the user's saved preferences (location, dietary, hobbies, interests, etc.) which could help in personalizing the response. If a query is provided, it will be used to filter for relevant preferences. 
- @get_tabs(): returns a list of opened tabs with each including url, title and a flag indicating if the tab is currently active to the user.
- @engine_search(query): searches the web using a search engine with the provided query if that makes the most sense. It will direct the user to browser's search result page and end the conversation.

Please evaluate the assistant’s response along these 6 dimensions:

1. Tool Call Accuracy:
   - If a tool was used:
     - Was it tools appropriate for the request?
     - Were parameters/values correct and specific?
     - Was the tool call redundant call (count as inappropriate)?
    - Anchors: 1 = clear mistakes or contradictions; 3 = minor slips without impact; 5 = fully consistent and precise.

2. Browser Context Awareness (1–5):
   - If applicable:
     - Did the assistant correctly track which tab is active and respect retrieved history/content?
     - Avoided referencing the wrong tab or contradicting tool outputs?
     - Anchors: 1 = clear mistakes or contradictions; 3 = minor slips without impact; 5 = fully consistent and precise.

3. Assistant Usefulness (1–5):
   - Did the assistant help achieve the user’s goal? Consider correctness, completeness, and clarity.
   - For @engine_search, judge whether the hand-off was appropriate and well-framed.
   - Anchors: 1 = unhelpful/incorrect; 3 = partially solves; 5 = fully solves or best-possible hand-off.

4. Preference Adherence (1–5):
   - If applicable:
     - Were given preferences honored faithfully in responses?
     - If preferences were irrelevant and not retrieved, score higher for that good judgment.
     - Anchors: 1 = ignored or misused; 3 = partial alignment or unnecessary retrieval; 5 = retrieved when helpful and honored correctly (or correctly skipped).

5. Response Conciseness (1–5):
   - Was the language concise and non-repetitive while still completing the task?
   - Anchors: 1 = verbose/redundant; 3 = somewhat wordy but acceptable; 5 = crisp and efficient.

6. Knowledge (1-5):
    - Was the model able to answer basic knowledge questions without resorting to a tool call?
    - Was the answer given by the model accurate and complete?
    - Anchors: 1 = the answer given was inaccurate/hallucinated; 3 = a tool call was used; 5 = returned complete and accurate answer without using an internet search or other tools.

Important:
- The assistant only sees browser content after it invokes a tool. Do not assume the assistant had access to page text, history descriptions, or preference details unless those were explicitly retrieved in the conversation.
- When judging tool call appropriateness, only consider what was visible to the assistant *before* each tool call.
- Some tool outputs (such as page contents) are truncated. Do not evaluate whether the assistant’s response fully covers or factually matches the original page. Only judge whether the assistant’s actions and outputs are reasonable given the truncated data it had.

** Only evaluate the assistant's most recent response. Do not evaluate any responses that occur earlier in the conversation **

---

Below is conversation history between a user and the brower assistant, ending with a user query:

{conversation}

Below is the assistant's most recent response:

{response}

---

Output your evaluation as a JSON object with this format:

{{
  "tool_call_accuracy": <int 1-5>,
  "browser_context_awareness": <int 1-5>,
  "assistant_usefulness": <int 1-5>,
  "preference_adherence": <int 1-5>,
  "response_conciseness": <int 1-5>,
  "knowledge": <int 1-5>,
  "explanation": "Brief rationale for each score referencing specific turns/tool calls.",
  "issues": ["optional short tags like 'redundant_call', 'wrong_tab', 'ignored_prefs'"]
}}"""