# CMPUT 455 Assignment 4 starter code
# This implements a random player.
# Implement your own Heap Go player in cmd_genmove to complete the assignment
# Full assignment specification and game rules on Canvas

import random

from heapgo import *  # the Heap Go game and command interface


class Player(CommandInterface):
    def __init__(self) -> None:
        super().__init__()
        # you can add your own initialisation here

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
        # you need to replace this random move by a move from your
        # own Heap Go player
        move = random.choice(moves)
        self.game.play(move)
        print(move)
        return True
#============================================================================
# End of functions requiring implementation
#============================================================================


if __name__ == "__main__":
    interface = Player()
    interface.main_loop()
