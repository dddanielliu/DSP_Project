import os
import sys

import pandas as pd
from pandas.errors import EmptyDataError

from . import similarity_search


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
        verbose=True, config={"recursion_limit": 100}
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


def main():
    for f in os.listdir("../question_crawl/csvs"):
        f = "test.csv"
        result_csv = "evaluation_results_test.csv"
        print(f"Evaluating file: {f}")
        df = get_qa_from_csv(os.path.join("../question_crawl/csvs", f))
        if df.empty:
            continue
        for _, row in df.iterrows():
            idx = row["number"]
            question = row["question"]
            answer = row["answer"]
            print("-----")
            print(f"#Q{idx} Question: {question}")
            response = ask(question)
            print(f"Model Answer: {response}")
            print(f"Correct Answer: {answer}")
            if not os.path.exists(result_csv):
                with open(result_csv, "w", encoding="utf-8") as out_f:
                    out_f.write(
                        '"file","number","question","model_answer","correct_answer"\n'
                    )
            with open(result_csv, "a", encoding="utf-8") as out_f:
                out_f.write(f'"{f}","{idx}","{question}","{response}","{answer}"\n')
        break


if __name__ == "__main__":
    main()
