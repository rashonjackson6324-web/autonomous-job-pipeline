import os
import pathlib
import anthropic
import sys

def _load_profile() -> str:
    """Candidate profile is user data, not source.

    Set CANDIDATE_PROFILE to a path, or drop a file at ./profile.md
    (see profile.example.md for the expected shape). profile.md is gitignored.
    """
    path = pathlib.Path(os.getenv("CANDIDATE_PROFILE", "profile.md"))
    if not path.exists():
        raise FileNotFoundError(
            f"No candidate profile at {path}. Copy profile.example.md to "
            "profile.md and fill it in, or set CANDIDATE_PROFILE."
        )
    return path.read_text(encoding="utf-8")


RESUME = _load_profile()

def answer_question(question):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = f"""You are helping the candidate answer a job application or interview question.
Use his background and career stories to craft the best possible answer.

the operator's Background:
{RESUME}

Question to answer:
{question}

Instructions:
- Use the STAR method where appropriate (Situation, Task, Action, Result)
- Select the most relevant career story
- Keep answer between 150-250 words
- Professional and confident tone
- Focus on specific results and metrics
- First person voice as the operator"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

if __name__ == "__main__":
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = input("Enter your application question: ")

    print("\nGenerating answer...\n")
    answer = answer_question(question)
    print(answer)