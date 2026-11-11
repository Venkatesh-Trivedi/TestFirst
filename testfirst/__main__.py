"""Run the terminal game with python -m testfirst."""

from .engine import Game, Outcome


def show_challenge(game: Game) -> None:
    print(f"\nTestFirst: {game.challenge.title}")
    print(game.challenge.specification)
    print(f"\n{game.challenge.source}\n")
    print("Enter a JSON list of 1-8 integers, each from -20 to 20.")
    print("At the list prompt: hint = optional hint, restart = reset hints, quit = exit.")


def main() -> None:
    game = Game()
    show_challenge(game)
    try:
        while True:
            text = input("\nList (or hint/restart/quit): ").strip()
            if text.lower() == "quit":
                break
            if text.lower() == "hint":
                print(game.next_hint() or "All hints have been used.")
                print(f"Hints used: {game.hints_used}/{len(game.challenge.hints)}")
                continue
            if text.lower() == "restart":
                game.restart()
                show_challenge(game)
                print("Restarted. Hints used: 0")
                continue
            prediction = input("Predicted correct output (JSON integer): ")
            result = game.evaluate(text, prediction)
            if result.outcome is Outcome.INVALID_INPUT:
                print(f"Invalid input: {result.message}")
            else:
                print(result.message)
            if result.outcome is Outcome.SUCCESS:
                print(f"Expected output: {result.expected}")
                print(f"Actual buggy output: {result.actual}")
                print("Trace of the buggy function:")
                for index, step in enumerate(result.trace):
                    if step.number is None:
                        print(f"  Initial: best = {step.best_after} (before the loop)")
                    else:
                        decision = "update" if step.updated else "no update"
                        print(
                            f"  Iteration {index}: number = {step.number}; "
                            f"{step.number} > {step.best_before} is {step.updated}; "
                            f"{decision}; best: {step.best_before} -> {step.best_after}"
                        )
                print(game.challenge.explanation)
                print(f"Hints used: {game.hints_used}/{len(game.challenge.hints)}")
            print("Try another list, request a hint, restart, or quit.")
    except (EOFError, KeyboardInterrupt):
        print()
    print(f"Goodbye! Hints used: {game.hints_used}/{len(game.challenge.hints)}")


if __name__ == "__main__":
    main()
