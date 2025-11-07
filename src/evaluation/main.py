import os
import re
import sys
import traceback

import pandas as pd
from pandas.errors import EmptyDataError

from ..laws_database import similarity_search


def get_qa_from_csv(file_path: str):
    try:
        df = pd.read_csv(file_path)
    except EmptyDataError:
        print(f"The file at {file_path} is empty.", file=sys.stderr)
        return pd.DataFrame(columns=["number", "answer", "question"])
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return pd.DataFrame(columns=["number", "answer", "question"])
    return df


def ask(query: str):
    agent = similarity_search.create_law_assistant_agent(
        verbose=True, config={"recursion_limit": 100}, model_name="gpt-oss:20b"
    )

    # First, perform a manual retrieval for the user's original query
    # and pass that retrieval to the agent as an assistant message. The
    # agent can then decide to call the `retrieve_context` tool again
    # (e.g., for individual options or refined queries) per its
    # system prompt rules.
    serialized_str, documents = similarity_search.manual_retrieve_context(query)

    # Build a messages payload: user question first, then an assistant
    # message that contains the initial retrieval. This ensures the
    # agent sees the original question clearly while also having the
    # retrieval available to consult.
    messages = [
        {"role": "user", "content": query},
    ]
    if serialized_str:
        messages.append(
            {
                "role": "assistant",
                "content": f"初次 retrieve_context 結果：\n{serialized_str}",
            }
        )

    # result = agent.invoke({"messages": messages})
    # return result["messages"][-1].content

    result = ""
    for token, metadata in agent.stream(
        {"messages": messages},
        stream_mode="messages",
    ):
        # print(f"node: {metadata['langgraph_node']}")
        # print(f"content: {token.content_blocks}")
        # print("\n")
        # print(token, metadata)
        if metadata['langgraph_node'] == 'model':
            # print(token.content_blocks)
            if token.content_blocks and token.content_blocks[0].get('type', '') == 'text':
                result += token.content_blocks[0].get('text', '')
                print(token.content_blocks[0].get('text', ''), end='', flush=True, file=sys.stderr)
            elif token.content_blocks and token.content_blocks[0].get('type', '') in ['tool_call_chunk']:
                pass

        elif metadata['langgraph_node'] in ['tools']:
            pass
        else:
            print(f"node: {metadata['langgraph_node']}", flush=True, file=sys.stderr)
            print(token.content_blocks, end='', flush=True, file=sys.stderr)
    final_answer = result.strip().split("\n")[-1]

    return final_answer

def try_ask(question: str) -> str:
    response = ""
    try_times = 0
    while True:
        try_times += 1
        if try_times > 10:
            print("FAILED")
            break
        try:
            if try_times > 7:
                print("FINAL TRIES:")
                response = ask(
                    question+
                    ("請直接輸出正確的選項編號（例如：1、2、3、4、A、B、C、D）。\n"
                    "不要輸出解釋或其他文字。\n"
                    "答案格式：只輸出數字或英文字母。\n"
                    "如果不確定，也請選最可能的答案。")
                )
            else:
                response = ask(question)
                # print(response)
                # print(response.strip())
                # for idx, c in enumerate(response.strip()):
                #     print(f"[{idx}]:\t|{c}|")
                # print(response.strip()[-1])
                # print((not response))
                # print(response.strip()[-1] == "…")

            if not response or response.strip()[-1] == "…" or len(response.strip().split('|'))<2:
                raise Exception("model output incorrect")
            break
        except Exception:
            print("Error during ask():")
            print(traceback.format_exc())
            print("Retrying...")
    return response

def main():
    for f in os.listdir(os.path.join(os.path.dirname(__file__),"..","question_crawl", "csvs")):
        result_csv = os.path.join(os.path.dirname(__file__),"evaluation_results.csv")
        print(f"Evaluating file: {f}")
        df = get_qa_from_csv(os.path.join(os.path.dirname(__file__),"..","question_crawl", "csvs", f))
        if df.empty:
            continue
        for _, row in df.iterrows():
            idx = row["number"]
            question = row["question"]
            answer = row["answer"]
            print("-----")
            print(f"#Q{idx} Question: {question}")
            
            response = try_ask(question)
            print()
            response = response.split('|')[-1]
            # match = re.search(r'([A-Za-z0-9]+)$', response.strip())
            # if match:
            #     response = match.group(1)
            print(f"Model Answer: {response}")
            print(f"Correct Answer: {answer}")
            row = pd.DataFrame([{
                "file": f,
                "number": idx,
                "question": question,
                "model_answer": response,
                "correct_answer": answer
            }])
            result_path = os.path.join(os.path.dirname(__file__), result_csv)
            if not os.path.exists(result_path):
                row.to_csv(result_path, index=False, encoding="utf-8")
            else:
                row.to_csv(result_path, mode="a", index=False, header=False, encoding="utf-8")
        break


if __name__ == "__main__":
    main()
