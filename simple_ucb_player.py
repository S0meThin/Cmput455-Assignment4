# CMPUT 455 Assignment 4 public player: flat Monte Carlo
# The a4.py starter code, with genmove from the assignment 3 sample solution:
# for each legal move, run simulations with the random policy (uniformly
# random legal moves), and play the move with the highest win rate.
# Instead of a fixed number of simulations per move,
# it keeps simulating, one simulation per move in each round, until
# GENMOVE_TIME is used up.
# Full assignment specification and game rules on Canvas

# The FlatMC Player edited to use UCB over a random policy.

import random
import time
import math
from typing import List

from heapgo import *  # the Heap Go game and command interface

# ---------------------------------------------------------------------------
# Flat Monte Carlo player settings
# ---------------------------------------------------------------------------
GENMOVE_TIME = 1.0  # seconds of simulations per genmove
C = math.sqrt(2)


class Player(CommandInterface):
    def __init__(self) -> None:
        super().__init__()
        self.policy = "random"  # A3 policy used in the simulations

# ============================================================================
# You need to implement or modify the following methods.
# ============================================================================
    def cmd_genmove(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        moves = self.game.legal_moves()
        if not moves:
            print_error("no legal moves")
            return False
        # Flat Monte Carlo, as in the assignment 3 sample solution, but with
        # a time limit instead of a fixed number of simulations per move
        best_move = moves[0]
        best_move_index = 0
        if len(moves) > 1:
            player = self.game.toplay
            wins = [0] * len(moves)
            visits = [0] * len(moves)
            n_simulations = 0
            deadline = time.time() + GENMOVE_TIME
            while time.time() < deadline:
                max_ucb = -9E9
                for i, move in enumerate(moves):
                    ucb = self.calculate_ucb(
                        move, visits[i], wins[i], n_simulations)
                    if ucb > max_ucb:
                        max_ucb = ucb
                        best_move = move
                        best_move_index = i

                game = self.game.copy()
                game.play(best_move)
                if self.simulate(game) == player:
                    wins[best_move_index] += 1
                visits[best_move_index] += 1
                n_simulations += 1

            best_win_rate = -1.0
            for i, move in enumerate(moves):
                if visits[i] != 0:
                    win_rate = wins[i] / visits[i]
                else:
                    win_rate = 0
                if win_rate > best_win_rate:
                    best_win_rate = win_rate
                    best_move = move
            best_move_i = visits.index(max(visits))
            best_move = moves[best_move_i]
            print_error("flat MC with UCB: {} simulations per move, move {} win rate {:.2f}".format(
                n_simulations, best_move, best_win_rate))
        move = best_move
        self.game.play(move)
        print(move)
        return True

    def calculate_ucb(self, move, visits, wins, total):
        if visits == 0:
            return 9E9
        ucb = wins / visits + C * math.sqrt(math.log(total) / visits)
        return ucb

    def policy_weights(self, game: HeapGo) -> List[float]:
        moves = game.legal_moves()

        if self.policy == "random":
            weights = [1] * len(moves)
        else:
            weights = []
            for move in moves:
                heap = game.heaps[move]
                i = len(heap) - 1
                weight = 0

                # Rule 1: all of the player's own tokens on top
                while i >= 0 and heap[i][0] == game.toplay:
                    weight += heap[i][1]
                    i -= 1

                # Rule 2: then one opponent token, if any are left
                if i >= 0:
                    weight += heap[i][1]

                weights.append(weight)

        return weights

    def simulate(self, game: HeapGo) -> str:
        moves = game.legal_moves()
        while moves:
            game.play(random.choices(
                moves, weights=self.policy_weights(game))[0])
            moves = game.legal_moves()

        return game.winner()

# ============================================================================
# End of functions requiring implementation
# ============================================================================


if __name__ == "__main__":
    interface = Player()
    interface.main_loop()
