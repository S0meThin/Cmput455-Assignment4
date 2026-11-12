# The player from assignment 3.

import math
import random
import time
from typing import List, Optional, Tuple

from heapgo import *


# ---------------------------------------------------------------------------
# A2: solver constants
# ---------------------------------------------------------------------------
INFINITY = 1 << 30
CHECK_NODES = 1024  # how often the search looks at the clock

EXACT, LOWER, UPPER = 0, 1, 2  # what a transposition table value says

SIZE_BITS = 5  # bits per heap size in a state key, enough for MAX_TOKENS
TOPLAY_BIT = 1 << (SIZE_BITS * MAX_HEAPS)
TT_BITS = 20
# Fibonacci hashing: multiply, keep 64 bits, and use the top ones, so that
# every bit of the key, not just the size of the first few heaps, picks the slot
TT_MULTIPLIER = 0x9E3779B97F4A7C15
TT_MASK64 = (1 << 64) - 1
TT_SHIFT = 64 - TT_BITS
# ---------------------------------------------------------------------------
# A2: end of solver constants
# ---------------------------------------------------------------------------


# ============================================================================
# A2: the solver
# ============================================================================
class Timeout(Exception):
    pass


class Solver:
    """Negamax with alpha-beta pruning, move ordering and a transposition
    table, on the score difference.  The value of a position is the best
    reachable (points for the player to move) - (points for the opponent),
    counting only the points still to be won.  The player to move wins when
    the score difference so far plus that value is positive."""

    def __init__(self) -> None:
        self.tt: List[Optional[Tuple[int, int, int, int]]] = [
            None] * (1 << TT_BITS)
        self.deadline = 0.0
        self.nodes = 0

    def new_game(self) -> None:
        """Table entries are keyed by heap sizes, so they only stay valid
        while the heaps themselves do not change."""
        self.tt = [None] * (1 << TT_BITS)

    def prepare(self, game: HeapGo) -> None:
        """Precompute what a move takes, for every color, heap and heap size.
        The search then never has to look at a token again."""
        self.num_heaps = len(game.heaps)
        self.gain: List[List[List[int]]] = [[], []]
        self.take: List[List[List[int]]] = [[], []]
        for color_index, color in enumerate(COLORS):
            for heap in game.heaps:
                gains, takes = [0], [0]  # nothing to take from an empty heap
                for size in range(1, len(heap) + 1):
                    taken, gained = 0, 0
                    while taken < size and heap[size - 1 - taken][0] == color:
                        gained += heap[size - 1 - taken][1]
                        taken += 1
                    if taken < size:
                        gained += heap[size - 1 - taken][1]
                        taken += 1
                    gains.append(gained)
                    takes.append(taken)
                self.gain[color_index].append(gains)
                self.take[color_index].append(takes)

    def solve(self, game: HeapGo, timelimit: int) -> Optional[Tuple[str, Optional[int]]]:
        """Returns (winner, move), or None when the time limit runs out.
        The move is the one to play when the player to move wins, else None."""
        self.nodes = 0
        self.deadline = time.time() + timelimit
        difference = game.score[game.toplay] - \
            game.score[opponent(game.toplay)]
        if game.game_over():
            value, move = 0, None
        else:
            try:
                value, move = self.root(game, difference)
            except Timeout:
                return None
        if difference + value > 0:
            return game.toplay, move
        return opponent(game.toplay), None

    def root(self, game: HeapGo, difference: float) -> Tuple[int, int]:
        self.prepare(game)
        sizes = [len(heap) for heap in game.heaps]
        key = sum(size << (SIZE_BITS * i) for i, size in enumerate(sizes))
        if game.toplay == WHITE:
            key |= TOPLAY_BIT
        # All that solve has to report is who wins, so search with the
        # narrowest window that still answers that question.
        threshold = math.ceil(-difference)
        alpha, beta = threshold - 1, threshold
        toplay = COLORS.index(game.toplay)
        gain, take = self.gain[toplay], self.take[toplay]
        best, best_move = -INFINITY, -1
        for move in self.moves(sizes, toplay, -1):
            size = sizes[move]
            taken, gained = take[move][size], gain[move][size]
            sizes[move] = size - taken
            value = gained - self.search(
                sizes, 1 - toplay, (key ^ TOPLAY_BIT) -
                (taken << (SIZE_BITS * move)),
                gained - beta, gained - alpha)
            sizes[move] = size
            if value > best:
                best, best_move = value, move
                if value > alpha:
                    alpha = value
                    if alpha >= beta:
                        break
        return best, best_move

    def search(self, sizes: List[int], toplay: int, key: int,
               alpha: int, beta: int) -> int:
        self.nodes += 1
        if self.nodes % CHECK_NODES == 0 and time.time() > self.deadline:
            raise Timeout
        alpha_original = alpha
        tt_move = -1
        slot = ((key * TT_MULTIPLIER) & TT_MASK64) >> TT_SHIFT
        entry = self.tt[slot]
        if entry is not None and entry[0] == key:
            value, flag, tt_move = entry[1], entry[2], entry[3]
            if flag == EXACT:
                return value
            if flag == LOWER:
                if value > alpha:
                    alpha = value
            elif value < beta:
                beta = value
            if alpha >= beta:
                return value
        moves = self.moves(sizes, toplay, tt_move)
        if not moves:
            return 0
        gain, take = self.gain[toplay], self.take[toplay]
        child_toplay, child_key = 1 - toplay, key ^ TOPLAY_BIT
        best, best_move = -INFINITY, moves[0]
        for move in moves:
            size = sizes[move]
            taken, gained = take[move][size], gain[move][size]
            sizes[move] = size - taken
            value = gained - self.search(
                sizes, child_toplay, child_key - (taken << (SIZE_BITS * move)),
                gained - beta, gained - alpha)
            sizes[move] = size
            if value > best:
                best, best_move = value, move
                if value > alpha:
                    alpha = value
                    if alpha >= beta:
                        break
        if best <= alpha_original:
            flag = UPPER
        elif best >= beta:
            flag = LOWER
        else:
            flag = EXACT
        self.tt[slot] = (key, best, flag, best_move)
        return best

    def moves(self, sizes: List[int], toplay: int, tt_move: int) -> List[int]:
        """Legal moves, best first: the move from the table, then the moves
        that win the most points now."""
        moves = [i for i in range(self.num_heaps) if sizes[i]]
        if len(moves) < 2:
            return moves
        gain = self.gain[toplay]
        moves.sort(key=lambda move: -gain[move][sizes[move]])
        if tt_move >= 0 and tt_move != moves[0] and sizes[tt_move]:
            moves.remove(tt_move)
            moves.insert(0, tt_move)
        return moves

# ============================================================================
# A2: end of the solver
# ============================================================================


# A3 Simulation:

class Simulation:
    def __init__(self):
        self.number_of_simulations = 10
        self.policy_type = 'random'

    def random_policy(self, game: HeapGo):
        if game.game_over():
            return game.winner()

        heap_number = random.choice(game.legal_moves())
        taken, gained = game.play_move(heap_number)
        winner = self.random_policy(game)
        game.undo_move(heap_number, taken, gained)

        return winner

    def probabilistic_policy(self, game: HeapGo):
        if game.game_over():
            return game.winner()

        probabilities, moves = self.get_probabilities_for_moves(game)

        move = random.choices(moves, weights=probabilities, k=1)[0]

        taken, gained = game.play_move(move)
        winner = self.probabilistic_policy(game)
        game.undo_move(move, taken, gained)

        return winner

    def get_probabilities_for_moves(self, game: HeapGo) -> List:
        moves = game.legal_moves()
        if len(moves) == 0:
            return [], []
        if self.policy_type == 'probabilistic':
            weights = [0]*len(moves)
            total = 0
            for index in range(len(moves)):
                taken, gained = game.play_move(moves[index])
                weights[index] += gained
                game.undo_move(moves[index], taken, gained)
                total += gained

            probabilities = [0]*len(weights)
            for index in range(len(weights)):
                probabilities[index] = float(weights[index])/total
            return probabilities, moves

        elif self.policy_type == 'random':
            probabilities = [1/len(moves)]*len(moves)
            return probabilities, moves
        return None

    def run_policy(self, game: HeapGo):
        if self.policy_type == 'random':
            return self.random_policy(game)
        elif self.policy_type == 'probabilistic':
            return self.probabilistic_policy(game)
        return None

    def simulation_round(self, game: HeapGo):
        wins = 0
        for i in range(self.number_of_simulations):
            winner = self.run_policy(game)
            # draws are impossible, so we return # of wins for the other player(we played a move before in genmove)
            if winner != game.toplay:
                wins += 1
        return wins

# A3 end of simulation


class Player(CommandInterface):
    def __init__(self) -> None:
        super().__init__()
        self.solver = Solver()
        self.simulation = Simulation()

    def cmd_heapgo(self, args: str) -> bool:
        if not super().cmd_heapgo(args):
            return False
        self.solver.new_game()  # A2
        return True

    def cmd_genmove(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        moves = self.game.legal_moves()
        if not moves:
            print_error("no legal moves")
            return False
        # you need to replace this random move by a move from your
        # simulation-based player
        wins = [0]*len(moves)
        for index in range(len(moves)):
            taken, gained = self.game.play_move(moves[index])
            wins[index] = self.simulation.simulation_round(self.game)
            self.game.undo_move(moves[index], taken, gained)

        move_to_play = moves[wins.index(max(wins))]
        self.game.play(move_to_play)
        print(move_to_play)
        return True


if __name__ == "__main__":
    interface = Player()
    interface.main_loop()
