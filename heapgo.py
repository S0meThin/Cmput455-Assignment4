# CMPUT 455 Assignment 4 Heap Go game and command interface
# Imported by a4.py and by the public players. Each of them implements genmove.
# Full assignment specification and game rules on Canvas

import ast
from sys import stderr
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Assignment restrictions (see assignment page)
# ---------------------------------------------------------------------------
MIN_HEAPS = 1
MAX_HEAPS = 20
MIN_TOKENS = 1
MAX_TOKENS = 20
MIN_VALUE = 1
MAX_VALUE = 20
KOMI_LIMIT = 100  # -100 < komi < 100, and komi must be an integer + 0.5

BLACK = 'b'
WHITE = 'w'
COLORS = (BLACK, WHITE)

Token = Tuple[str, int]
Heap = List[Token]
Heaps = List[Heap]


def not_yet() -> bool:
    raise NotImplementedError("Command not implemented.")
    return False


def print_error(error: str) -> None:
    print(error, file=stderr)


def opponent(color: str) -> str:
    return WHITE if color == BLACK else BLACK


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
def is_int(obj: Any) -> bool:
    # bool is a subclass of int; True/False are not valid values
    return isinstance(obj, int) and not isinstance(obj, bool)


def is_token(obj: Any) -> bool:
    return (isinstance(obj, tuple)
            and len(obj) == 2
            and obj[0] in COLORS
            and is_int(obj[1])
            and MIN_VALUE <= obj[1] <= MAX_VALUE)


def is_heap(obj: Any) -> bool:
    return (isinstance(obj, list)
            and MIN_TOKENS <= len(obj) <= MAX_TOKENS
            and all(is_token(token) for token in obj))


def is_heaps(obj: Any) -> bool:
    return (isinstance(obj, list)
            and MIN_HEAPS <= len(obj) <= MAX_HEAPS
            and all(is_heap(heap) for heap in obj))


def parse_komi(text: str) -> Optional[float]:
    try:
        komi = float(text)
    except ValueError:
        return None
    if not (-KOMI_LIMIT < komi < KOMI_LIMIT):
        return None
    if (komi - 0.5) != int(komi - 0.5):
        return None
    return komi


def parse_heaps(text: str) -> Optional[Heaps]:
    try:
        parsed = ast.literal_eval(text)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return None
    if not is_heaps(parsed):
        return None
    return parsed


def parse_heap_number(args: str) -> Optional[int]:
    parts = args.split()
    if len(parts) != 1:
        return None
    try:
        return int(parts[0])
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class HeapGo:
    def __init__(self, komi: float, heaps: Heaps) -> None:
        self.komi = komi
        self.heaps = heaps
        self.toplay = BLACK
        self.score = {BLACK: 0, WHITE: komi}

    def __str__(self) -> str:
        return "k {} {}".format(self.komi, self.heaps)

    def is_legal(self, heap_number: int) -> bool:
        return 0 <= heap_number < len(self.heaps) and len(self.heaps[heap_number]) > 0

    def legal_moves(self) -> List[int]:
        return [i for i in range(len(self.heaps)) if self.is_legal(i)]

    def game_over(self) -> bool:
        return len(self.legal_moves()) == 0

    def play(self, heap_number: int) -> bool:
        if not self.is_legal(heap_number):
            return False
        self.play_move(heap_number)  # A2: the rules moved into play_move
        return True

    def winner(self) -> Optional[str]:
        if not self.game_over():
            return None
        if self.score[BLACK] > self.score[WHITE]:
            return BLACK
        if self.score[WHITE] > self.score[BLACK]:
            return WHITE
        return None  # draw; impossible with komi = integer + 0.5

# ============================================================================
# A2: play_move / undo_move / copy
# ============================================================================
    def play_move(self, heap_number: int) -> Tuple[Heap, int]:
        """Play a legal move.  Returns what is needed to undo it."""
        heap = self.heaps[heap_number]
        taken = []
        # Rule 1: take all own-color tokens from the top
        while heap and heap[-1][0] == self.toplay:
            taken.append(heap.pop())
        # Rule 2: then one opponent token, if any remain
        if heap:
            taken.append(heap.pop())
        gained = sum(value for _, value in taken)
        self.score[self.toplay] += gained
        self.toplay = opponent(self.toplay)
        return taken, gained

    def undo_move(self, heap_number: int, taken: Heap, gained: int) -> None:
        self.toplay = opponent(self.toplay)
        self.score[self.toplay] -= gained
        self.heaps[heap_number].extend(reversed(taken))

    def copy(self) -> "HeapGo":
        game = HeapGo(self.komi, [list(heap) for heap in self.heaps])
        game.toplay = self.toplay
        game.score = dict(self.score)
        return game
# ============================================================================
# A2: end of game changes
# ============================================================================


CommandMap = Dict[str, Callable[[str], bool]]


class CommandInterface:
    def __init__(self) -> None:
        self.game: Optional[HeapGo] = None
        self.commands: CommandMap = {
            "help": self.cmd_help,
            "heapgo": self.cmd_heapgo,
            "show": self.cmd_show,
            "toplay": self.cmd_toplay,
            "play": self.cmd_play,
            "legal": self.cmd_legal,
            "genmove": self.cmd_genmove,
            "score": self.cmd_score,
            "winner": self.cmd_winner,
        }

# ============================================================================
# Command implementations
# ============================================================================
    def cmd_heapgo(self, args: str) -> bool:
        parts = args.split(maxsplit=1)
        if len(parts) != 2:
            print_error("usage: heapgo komi game")
            return False
        komi = parse_komi(parts[0])
        if komi is None:
            print_error("invalid komi: {}".format(parts[0]))
            return False
        heaps = parse_heaps(parts[1])
        if heaps is None:
            print_error("invalid game: {}".format(parts[1]))
            return False
        self.game = HeapGo(komi, heaps)
        return True

    def cmd_show(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        print(self.game)
        return True

    def cmd_toplay(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        if args not in COLORS:
            print_error("invalid color: {}".format(args))
            return False
        self.game.toplay = args
        return True

    def cmd_play(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        heap_number = parse_heap_number(args)
        if heap_number is None:
            print_error("invalid heap number: {}".format(args))
            return False
        if not self.game.play(heap_number):
            print_error("illegal move: {}".format(heap_number))
            return False
        return True

    def cmd_legal(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        heap_number = parse_heap_number(args)
        if heap_number is None:
            print_error("invalid heap number: {}".format(args))
            return False
        print("yes" if self.game.is_legal(heap_number) else "no")
        return True

    def cmd_score(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        print("b {} w {}".format(
            self.game.score[BLACK], self.game.score[WHITE]))
        return True

    def cmd_winner(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        winner = self.game.winner()
        if winner is None:
            print_error(
                "game not over" if not self.game.game_over() else "draw")
            return False
        print(winner)
        return True

    def cmd_genmove(self, args: str) -> bool:
        return not_yet()  # implemented by each player program

# ============================================================================
# Command processing
# ============================================================================
    def cmd_help(self, ignore_args: str) -> bool:
        print("\nKnown commands:")
        for cmd in self.commands:
            print(cmd)
        return True

    def process_command(self, cmd_name: str, cmd_args: str) -> None:
        status = "= -1"
        cmd = self.commands.get(cmd_name)
        if cmd:
            try:
                if cmd(cmd_args):
                    status = "= 1"
            except Exception as e:
                print_error(
                    f"Command {cmd_name} with arguments {cmd_args} failed with exception: {e}")
        else:
            print_error("Unknown command. Type 'help' for commands.")
        print(status)

    def main_loop(self) -> None:
        process_commands = True
        while process_commands:
            try:
                line = input()
            except EOFError:
                break
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(maxsplit=1)
            cmd_name = parts[0]
            if cmd_name == "exit":
                process_commands = False
                continue
            cmd_args = parts[1] if len(parts) > 1 else ""
            self.process_command(cmd_name, cmd_args)
