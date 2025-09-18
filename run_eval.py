import pandas as pd
from datasets import load_dataset
import os
import subprocess
import yaml
import json

## model providers
import openai
from openai import AsyncOpenAI
import together
from together import AsyncTogether

import asyncio
from tqdm.asyncio import tqdm_asyncio
from pydantic import BaseModel, Field
from typing import List
from absl import app, flags
from absl import logging as absl_logging

# prompts
import prompts as p

absl_logging.set_verbosity(absl_logging.ERROR)

FLAGS = flags.FLAGS
flags.DEFINE_string("model", "together.ai:Qwen/Qwen3-Next-80B-A3B-Thinking", "Name of model to evaluate and provider (formatted as <provider>:<model_id>")
flags.DEFINE_string("eval_model_id", "gpt-5", "Name of judge model (OpenAI assumed)")
flags.DEFINE_integer("max_concurrency", 10, "Maximum number of asynchronus processes to run")
flags.DEFINE_bool("skip_inference", False, "If set to True, we load inferences from existing, rather than predict")
flags.DEFINE_string("output_dir", "data", "Location into which output data will be saved")

EVAL_COLS = [
    "browser_context_awareness",
    "assistant_usefulness",
    "preference_adherence",
    "response_conciseness",
    "tool_call_accuracy",
    "knowledge"
    ]


def get_access_token():
    try:
        return subprocess.check_output(
            ["gcloud", "auth", "print-access-token"], 
            text=True).strip()
    except Exception e:
        print(f"ERROR retrieving Vertex token: {e}")

async_client_oa = AsyncOpenAI()    # auth is at os.environ["OPENAI_API_KEY"]
async_client_tg = AsyncTogether()  # auth is at os.environ["TOGETHER_API_KEY"]
async_client_groq = AsyncOpenAI(
    api_key=os.environ['GROQ_API_KEY'],
    base_url="https://api.groq.com/openai/v1",
)

REGION = "us-central1"
PROJECT_ID = os.environ.get("VERTEX_PROJECT_ID", "")
if not PROJECT_ID:
    print("WARN: VERTEX_PROJECT_ID not found in environment. This may cause issues when using vertex-hosted models")
# can only be used for gemini models
async_client_vertex = AsyncOpenAI(base_url=f"https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{REGION}/endpoints/openapi",
    api_key=get_access_token()
)


class EvalResponse(BaseModel):
    tool_call_accuracy: str
    browser_context_awareness: str 
    assistant_usefulness: str
    preference_adherence: str 	
    response_conciseness: str
    knowledge: str 	
    explanation: str
    issues: List[str] = Field(default_factory=list)


def get_tools():
    with open("tools.yaml", "r") as f:
        tools = yaml.safe_load(f)
    return tools


async def get_response(messages, provider, model_id, tools):

    match provider:
        case "together.ai":
            response = await async_client_tg.chat.completions.create(
                model=model_id,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
        case "openai":
            response = await async_client_oa.chat.completions.create(
                model=model_id,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
        case "groq":
            response = await async_client_groq.chat.completions.create(
                model=model_id,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
        case "vertex":
            response = await async_client_vertex.chat.completions.create(
                model=model_id,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
    
    return response


async def async_make_prediction(messages, provider, model_id, tools):
    try:
        response = await get_response(messages, provider, model_id, tools=tools)
    except Exception as e:
        print(f"ERROR: {e}")
        return {"error:", str(e)}   # need to stringify to store as json later

    message = response.choices[0].message
    return message.model_dump()


async def make_predictions(messages, provider, model_id, tools, limit=10):
    semaphore = asyncio.Semaphore(limit)

    async def bounded_prediction(message):
        async with semaphore:
            return await async_make_prediction(message, provider, model_id, tools)

    tasks = [bounded_prediction(message) for message in messages]
    return await tqdm_asyncio.gather(*tasks)


def format_conversation(conversation, keep_head=50, keep_tail=50):
    # truncate page content retrieval outputs if any
    truncated_convo = []
    for turn in conversation:
        if turn.get("role") == "tool":
            # Check if this tool response corresponds to get_page_contents
            tool_call_id = turn.get("tool_call_id")
            if tool_call_id:
                # To identify tool type, look back one step (assistant tool call)
                prev_turn = truncated_convo[-1] if truncated_convo else None
                if (
                    prev_turn
                    and prev_turn.get("role") == "assistant"
                    and "tool_calls" in prev_turn
                ):
                    for call in prev_turn["tool_calls"]:
                        if (
                            call["id"] == tool_call_id
                            and call["function"]["name"] == "get_page_contents"
                        ):
                            content = turn.get("content", "")
                            if isinstance(content, str) and len(content) > (keep_head + keep_tail):
                                turn["content"] = (
                                content[:keep_head]
                                + " ... [TRUNCATED] ... "
                                + content[-keep_tail:]
                            )
        truncated_convo.append(turn)
    return truncated_convo


async def evaluate_one(messages, resp, eval_model_id, tools):
    conversation = format_conversation(messages)
    judge_prompt = p.JUDGE_PROMPT.format(conversation=conversation, response=resp)

    response = await async_client_oa.chat.completions.parse(
                model=eval_model_id,
                messages=[{"role": "system", "content": judge_prompt}],
                response_format=EvalResponse
            )

    return json.loads(response.choices[0].message.content)


async def evaluate_all(messages_and_responses, eval_model_id, tools, limit=10):
    semaphore = asyncio.Semaphore(limit)

    async def bounded_evaluation(message, response):
        async with semaphore:
            return await evaluate_one(message, response, eval_model_id, tools)
    
    tasks = [bounded_evaluation(message, response) for message, response in messages_and_responses]
    return await tqdm_asyncio.gather(*tasks)


def fix_conversation(messages):
    ## HF adds some extra fields with cause issues with some providers
    new_messages = []
    for message in messages:
        new_messages.append({k:v for k,v in message.items() if v is not None})
    return new_messages
    

def main(_):
    tools = get_tools()
    provider, model_id = FLAGS.model.split(":")
    model_id_simple = model_id.split("/")[-1]
    print(" | ".join([provider, model_id, model_id_simple]))

    data = load_dataset("mozilla/chat-eval")['train'].to_pandas()

    os.makedirs(FLAGS.output_dir, exist_ok=True)
    conversations = data['conversation'].apply(fix_conversation)

    if not FLAGS.skip_inference:
        print("Making predictions")
        data[f"prediction_{model_id_simple}"] = asyncio.run(
            make_predictions(
                conversations, 
                provider=provider, 
                model_id=model_id, 
                tools=tools, 
                limit=FLAGS.max_concurrency
                )
            )
        data.to_json(f"{FLAGS.output_dir}/{model_id_simple}_predictions.json", orient="records")
    data = pd.read_json(f"{FLAGS.output_dir}/{model_id_simple}_predictions.json", orient="records")

    print("Evaluating model")
    evals = asyncio.run(
        evaluate_all(
            [(msg, pred) for msg, pred in data[['conversation', f'prediction_{model_id_simple}']].values], 
            eval_model_id=FLAGS.eval_model_id, tools=tools, limit=FLAGS.max_concurrency
            )
        )

    evals_df = pd.DataFrame(evals)
    evals_df.to_json(f"{FLAGS.output_dir}/{model_id_simple}_evals.json", orient="records")

    print("Finished evaluation. Results:")
    print(
        evals_df[EVAL_COLS].apply(pd.to_numeric, errors="coerce").mean()
    )


if __name__ == "__main__":
    app.run(main)
