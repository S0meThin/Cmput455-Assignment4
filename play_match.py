# CMPUT 455 Assignment 4 - play one game of Heap Go between two programs
#
# Usage: python3 play_match.py position_file black_player.py white_player.py [game_number]
#
# Example: python3 play_match.py heapgo1.txt a4.py public_negamax_player.py
#
# position_file contains one or more heapgo commands, such as
#   heapgo 12.5 [[('b', 3), ('w', 7)], [('w', 1)]]
# Lines starting with # are comments. By default the first heapgo command
# is used. The optional game_number selects another one, starting from 1,
# for example: python3 play_match.py positions.txt a4.py public_flatMC_player.py 3
# plays the third position in positions.txt.
#
# The script sends genmove to the player whose turn it is, then sends the
# chosen move to the other player with the play command, until no legal
# moves are left. It checks every move with its own copy of the rules.
# A player that crashes, runs out of time, answers with an error, or plays an
# illegal move loses the game immediately.
# The result is written to game_result.txt.

import ast
import os
import queue
import subprocess
import sys
import threading
import time
from typing import List, Optional, Tuple

TIME_LIMIT = 30         # seconds per genmove
SETUP_TIME_LIMIT = 10   # seconds for the heapgo and play commands
MEMORY_LIMIT = 1 << 30  # 1 GB per player, enforced on Linux only
RESULT_FILE = "game_result.txt"

BLACK = 'b'
WHITE = 'w'


def opponent(color: str) -> str:
    return WHITE if color == BLACK else BLACK


# ---------------------------------------------------------------------------
# Referee copy of the rules
# ---------------------------------------------------------------------------
class Referee:
    def __init__(self, komi: float, heaps: List[List[Tuple[str, int]]]) -> None:
        self.heaps = [list(heap) for heap in heaps]
        self.toplay = BLACK
        self.score = {BLACK: 0, WHITE: komi}

    def is_legal(self, heap_number: int) -> bool:
        return 0 <= heap_number < len(self.heaps) and len(self.heaps[heap_number]) > 0

    def game_over(self) -> bool:
        return all(len(heap) == 0 for heap in self.heaps)

    def play(self, heap_number: int) -> None:
        heap = self.heaps[heap_number]
        gained = 0
        # Rule 1: take all own-color tokens from the top
        while heap and heap[-1][0] == self.toplay:
            gained += heap.pop()[1]
        # Rule 2: then one opponent token, if any remain
        if heap:
            gained += heap.pop()[1]
        self.score[self.toplay] += gained
        self.toplay = opponent(self.toplay)

    def winner(self) -> str:
        return BLACK if self.score[BLACK] > self.score[WHITE] else WHITE


def read_position(path: str, number: int) -> Tuple[str, float, list]:
    """Return the number-th heapgo command in the file (counting from 1)."""
    commands = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("heapgo"):
                commands.append(line)
    if not 1 <= number <= len(commands):
        sys.exit("{} has {} heapgo commands, cannot use number {}".format(
            path, len(commands), number))
    command = commands[number - 1]
    parts = command.split(maxsplit=2)
    return command, float(parts[1]), ast.literal_eval(parts[2])


# ---------------------------------------------------------------------------
# Running a player program
# ---------------------------------------------------------------------------
def limit_memory() -> None:
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT, MEMORY_LIMIT))
    except (ImportError, ValueError, OSError):
        pass  # not supported on this system, e.g. macOS


class PlayerError(Exception):
    pass


class Player:
    def __init__(self, path: str) -> None:
        self.path = path
        self.name = os.path.basename(path)
        self.max_time = 0.0
        self.total_time = 0.0
        self.num_moves = 0
        self.process = subprocess.Popen(
            [sys.executable, path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, universal_newlines=True, bufsize=1,
            cwd=os.path.dirname(os.path.abspath(path)),
            preexec_fn=limit_memory if sys.platform.startswith("linux") else None)
        self.lines: "queue.Queue[Optional[str]]" = queue.Queue()
        reader = threading.Thread(target=self.read_lines, daemon=True)
        reader.start()

    def read_lines(self) -> None:
        for line in self.process.stdout:
            self.lines.put(line.strip())
        self.lines.put(None)  # end of output: the program has stopped

    def send(self, command: str, time_limit: float) -> Tuple[List[str], float]:
        """Send one command. Return its output lines and the time it took.
        Raise PlayerError if the program crashes, runs out of time,
        or answers with an error status."""
        start = time.time()
        try:
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()
        except (BrokenPipeError, OSError):
            raise PlayerError("crashed before command: " + command)
        output = []
        while True:
            remaining = start + time_limit - time.time()
            if remaining <= 0:
                raise PlayerError("timeout on command: " + command)
            try:
                line = self.lines.get(timeout=remaining)
            except queue.Empty:
                raise PlayerError("timeout on command: " + command)
            if line is None:
                raise PlayerError("crashed on command: " + command)
            if line == "= 1":
                return output, time.time() - start
            if line == "= -1":
                raise PlayerError("error status on command: " + command)
            if line:
                output.append(line)

    def genmove(self) -> int:
        output, used = self.send("genmove", TIME_LIMIT)
        self.max_time = max(self.max_time, used)
        self.total_time += used
        self.num_moves += 1
        try:
            return int(output[-1])
        except (IndexError, ValueError):
            raise PlayerError(
                "genmove answer is not a heap number: {}".format(output))

    def close(self) -> None:
        try:
            self.process.stdin.write("exit\n")
            self.process.stdin.flush()
            self.process.wait(timeout=2)
        except Exception:
            pass
        if self.process.poll() is None:
            self.process.kill()
        try:
            self.process.stdin.close()
        except Exception:
            pass  # the program may have crashed and closed its end already


# ---------------------------------------------------------------------------
# One game
# ---------------------------------------------------------------------------
def play_game(command: str, komi: float, heaps: list,
              black_path: str, white_path: str) -> List[str]:
    referee = Referee(komi, heaps)
    players = {BLACK: Player(black_path), WHITE: Player(white_path)}
    moves: List[int] = []
    winner, reason = None, "game over"
    try:
        for color in (BLACK, WHITE):
            try:
                players[color].send(command, SETUP_TIME_LIMIT)
            except PlayerError as e:
                winner, reason = opponent(color), "{} {}".format(color, e)
                raise
        while not referee.game_over():
            color = referee.toplay
            try:
                move = players[color].genmove()
            except PlayerError as e:
                winner, reason = opponent(color), "{} {}".format(color, e)
                raise
            if not referee.is_legal(move):
                winner, reason = opponent(
                    color), "{} played illegal move {}".format(color, move)
                raise PlayerError(reason)
            referee.play(move)
            moves.append(move)
            print("{} {} plays {:2d}   score b {} w {}".format(
                len(moves), color, move, referee.score[BLACK], referee.score[WHITE]))
            other = opponent(color)
            try:
                players[other].send("play {}".format(move), SETUP_TIME_LIMIT)
            except PlayerError as e:
                winner, reason = color, "{} {}".format(other, e)
                raise
        winner = referee.winner()
    except PlayerError:
        pass
    finally:
        for player in players.values():
            player.close()

    result = [
        "Position: {}".format(command),
        "Black: {}".format(players[BLACK].name),
        "White: {}".format(players[WHITE].name),
        "Winner: {} ({})".format(winner, players[winner].name),
        "Reason: {}".format(reason),
        "Final score: b {} w {}".format(
            referee.score[BLACK], referee.score[WHITE]),
        "Number of moves: {}".format(len(moves)),
        "Moves: {}".format(" ".join(str(move) for move in moves)),
    ]
    for color in (BLACK, WHITE):
        player = players[color]
        average = player.total_time / player.num_moves if player.num_moves else 0.0
        result.append("{} time per move: max {:.2f}s, average {:.2f}s".format(
            color, player.max_time, average))
    return result


def main() -> None:
    if len(sys.argv) not in (4, 5):
        sys.exit("usage: python3 play_match.py position_file black_player.py "
                 "white_player.py [game_number]")
    number = int(sys.argv[4]) if len(sys.argv) == 5 else 1
    command, komi, heaps = read_position(sys.argv[1], number)
    result = play_game(command, komi, heaps, sys.argv[2], sys.argv[3])
    with open(RESULT_FILE, "w") as f:
        f.write("\n".join(result) + "\n")
    print("\n".join(result))
    print("Result written to {}".format(RESULT_FILE))


if __name__ == "__main__":
    main()
