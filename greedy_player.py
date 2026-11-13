# Greedy player


from heapgo import *  # the Heap Go game and command interface


class Player(CommandInterface):
    def __init__(self) -> None:
        super().__init__()
        # you can add your own initialisation here

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

        # Always take the move that gives us the most points that turn
        best_move = moves[0]
        max_points = 0
        for move in moves:
            points = 0
            heap = self.game.heaps[move]
            j = len(heap) - 1

            # Rule 1: all of the player's own tokens on top
            while j >= 0 and heap[j][0] == self.game.toplay:
                points += heap[j][1]
                j -= 1

            # Rule 2: then one opponent token, if any are left
            if j >= 0:
                points += heap[j][1]

            if points > max_points:
                max_points = points
                best_move = move

        self.game.play(best_move)
        print(best_move)
        return True
# ============================================================================
# End of functions requiring implementation
# ============================================================================


if __name__ == "__main__":
    interface = Player()
    interface.main_loop()
