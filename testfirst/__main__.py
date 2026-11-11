"""Run the terminal game with python -m testfirst."""

from .challenges import CHALLENGES
from .engine import Game, Outcome, parse_numbers


def show_challenge(game: Game) -> None:
    print(f"\nTestFirst: {game.challenge.title}")
    print(game.challenge.specification)
    print(f"\n{game.challenge.source}\n")
    print(game.challenge.input_rules)
    print("At the list prompt: hint = optional hint, restart = reset hints, menu = choose challenge, quit = exit.")


def choose_game(games: list[Game]) -> Game | None:
    print("\nTestFirst challenge menu")
    for index, game in enumerate(games, 1):
        print(f"  {index}. {game.challenge.title}")
    while True:
        choice = input(f"Choose a challenge (1-{len(games)}), or quit: ").strip().lower()
        if choice == "quit":
            return None
        if choice in {str(index) for index in range(1, len(games) + 1)}:
            return games[int(choice) - 1]
        print("Invalid choice. Enter a challenge number or quit.")


def main() -> None:
    games = [Game(challenge) for challenge in CHALLENGES]
    game = None
    try:
        game = choose_game(games)
        if game is not None:
            show_challenge(game)
        while game is not None:
            text = input("\nList (or hint/restart/menu/quit): ").strip()
            if text.lower() == "quit":
                break
            if text.lower() == "menu":
                selected = choose_game(games)
                if selected is None:
                    break
                game = selected
                show_challenge(game)
                print(f"Hints used: {game.hints_used}/{len(game.challenge.hints)}")
                continue
            if text.lower() == "hint":
                print(game.next_hint() or "All hints have been used.")
                print(f"Hints used: {game.hints_used}/{len(game.challenge.hints)}")
                continue
            if text.lower() == "restart":
                game.restart()
                show_challenge(game)
                print("Restarted. Hints used: 0")
                continue
            try:
                parse_numbers(text, game.challenge)
            except ValueError as error:
                print(f"Invalid input: {error}")
                continue
            prediction = input("Predicted correct output (JSON integer): ")
            result = game.evaluate(text, prediction)
            if result.outcome is Outcome.INVALID_INPUT:
                print(f"Invalid input: {result.message}")
            else:
                print(result.message)
            if result.outcome is Outcome.SUCCESS:
                print("Challenge complete.")
                print(f"Expected output: {result.expected}")
                print(f"Actual buggy output: {result.actual}")
                print("Trace of the buggy function:")
                for step in result.trace:
                    print(f"  {step}")
                print(game.challenge.explanation)
                print(f"Hints used: {game.hints_used}/{len(game.challenge.hints)}")
            print("Try another list, request a hint, restart, choose menu, or quit.")
    except (EOFError, KeyboardInterrupt):
        print()
    if game is None:
        print("Goodbye!")
    else:
        print(f"Goodbye! Hints used: {game.hints_used}/{len(game.challenge.hints)}")


if __name__ == "__main__":
    main()
