"""Run the same authenticated training agent from a terminal."""

import argparse
import getpass
from src.agents.orchestrator import TrainingOrchestrator
from src.agents.worker import GatewayError
from src.tools import db_queries as db


def main():
    parser = argparse.ArgumentParser(description="AgentX training coach")
    parser.add_argument("--user", default="learner", help="Existing app account")
    parser.add_argument(
        "--question", help="Ask one question instead of starting a chat"
    )
    options = parser.parse_args()
    token = None
    try:
        agent = TrainingOrchestrator()
        db.init()
        token = db.login(options.user, getpass.getpass("Password: "))
        user = db.user(token)
        print(f"AgentX training coach · {agent.settings.mode_label}")
        print("Enter /quit to exit. Conversations are saved to your app account.")
        while True:
            question = (
                options.question
                if options.question is not None
                else input("\nYou: ").strip()
            )
            if question == "/quit":
                break
            if not question:
                if options.question is not None:
                    raise ValueError("Enter a nonempty question")
                continue
            try:
                result = agent.run(user, question)
                print("\nTools: " + " → ".join(result["trace"]))
                print("\nCoach: " + result["answer"])
                for source in result["sources"]:
                    print(
                        f"  [{source['citation']}] {source['title']} · Section {source['section']}"
                    )
            except (ValueError, GatewayError) as exc:
                print(f"Unable to answer: {exc}")
                if options.question is not None:
                    return 1
            if options.question is not None:
                break
        return 0
    except (ValueError, GatewayError) as exc:
        print(f"Unable to start: {exc}")
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye.")
        return 0
    finally:
        if token:
            db.logout(token)


if __name__ == "__main__":
    raise SystemExit(main())
