# CMPUT 455 Assignment 4 public player: iterative deepening alphabeta (negamax form)
# The a4.py starter code, with a genmove based on the lecture slides:
# depth-limited alphabeta, no transposition table.
# The evaluation at the depth limit is the score difference for the player
# to move. genmove searches depth 1, 2, 3, ... until GENMOVE_TIME is used up,
# and plays the best move of the deepest completed search.
# Full assignment specification and game rules on Canvas

import time
from typing import List

from heapgo import *  # the Heap Go game and command interface

# ---------------------------------------------------------------------------
# Negamax player settings
# ---------------------------------------------------------------------------
GENMOVE_TIME = 1.0  # seconds of search per genmove
CHECK_NODES = 1000  # how often the search looks at the clock
INFINITY = float("inf")


class Timeout(Exception):
    pass


class Player(CommandInterface):
#============================================================================
# You need to implement or modify the following methods.
#============================================================================
    def cmd_genmove(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        moves = self.game.legal_moves()
        if not moves:
            print_error("no legal moves")
            return False
        move = self.iterative_deepening(moves)
        self.game.play(move)
        print(move)
        return True

    def iterative_deepening(self, moves: List[int]) -> int:
        if len(moves) == 1:
            return moves[0]
        self.deadline = time.time() + GENMOVE_TIME
        self.nodes = 0
        tokens_left = sum(len(heap) for heap in self.game.heaps)
        best_move = moves[0]
        depth = 1
        while depth <= tokens_left:  # no game lasts longer than this
            # search a copy, so a timeout in the middle of a search
            # does not leave the real game in a wrong state
            game = self.game.copy()
            try:
                best_move = self.search_root(game, moves, depth)
            except Timeout:
                break
            depth += 1
        print_error("negamax: completed depth {}, best move {}".format(depth - 1, best_move))
        return best_move

    def check_time(self) -> None:
        self.nodes += 1
        if self.nodes % CHECK_NODES == 0 and time.time() > self.deadline:
            raise Timeout

    def evaluate(self, game: HeapGo) -> float:
        """Statically evaluate for the player to move: the score difference.
        At the end of the game, this is the exact result."""
        return game.score[game.toplay] - game.score[opponent(game.toplay)]

    def search_root(self, game: HeapGo, moves: List[int], depth: int) -> int:
        alpha, best_move = -INFINITY, moves[0]
        for move in moves:
            taken, gained = game.play_move(move)
            value = -self.alphabeta(game, -INFINITY, -alpha, depth - 1)
            game.undo_move(move, taken, gained)
            if value > alpha:
                alpha, best_move = value, move
        return best_move

    def alphabeta(self, game: HeapGo, alpha: float, beta: float, depth: int) -> float:
        """Depth-limited alphabeta from the lecture slides."""
        self.check_time()
        moves = game.legal_moves()
        if not moves or depth == 0:
            return self.evaluate(game)
        for move in moves:
            taken, gained = game.play_move(move)
            value = -self.alphabeta(game, -beta, -alpha, depth - 1)
            if value > alpha:
                alpha = value
            game.undo_move(move, taken, gained)
            if value >= beta:
                return beta  # or value - see failsoft
        return alpha

#============================================================================
# End of functions requiring implementation
#============================================================================


if __name__ == "__main__":
    interface = Player()
    interface.main_loop()
