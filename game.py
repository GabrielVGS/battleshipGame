import socket
import threading
import json
import random


class BattleshipGame:
    def __init__(self):
        self.board_size = 10
        self.ships = [5, 4, 3, 3, 2]  # Tamanho dos navios
        self.players = {}
        self.current_turn = None
        self.game_phase = "setup"  # Fases: 'setup', 'playing', 'game_over'
        self.game_over = False

    def create_empty_board(self):
        return [["~" for _ in range(self.board_size)] for _ in range(self.board_size)]

    def is_valid_placement(self, board, row, col, length, direction):
        if direction.upper() == "H":  # Horizontal
            if col + length > self.board_size:
                return False
            for c in range(col, col + length):
                if board[row][c] != "~":
                    return False
        elif direction.upper() == "V":  # Vertical
            if row + length > self.board_size:
                return False
            for r in range(row, row + length):
                if board[r][col] != "~":
                    return False
        else:
            return False  # Direção inválida
        return True

    def place_ship(self, board, row, col, length, direction):
        if direction.upper() == "H":
            for c in range(col, col + length):
                board[row][c] = "S"
        else:
            for r in range(row, row + length):
                board[r][col] = "S"

    def auto_place_ships(self, board):
        for ship_length in self.ships:
            placed = False
            attempts = 0
            while not placed and attempts < 100:
                row = random.randint(0, self.board_size - 1)
                col = random.randint(0, self.board_size - 1)
                direction = random.choice(["H", "V"])

                if self.is_valid_placement(board, row, col, ship_length, direction):
                    self.place_ship(board, row, col, ship_length, direction)
                    placed = True
                attempts += 1
        return placed

    def make_shot(self, player_id, target_row, target_col):
        if self.current_turn != player_id or self.game_phase != "playing":
            return False, "Não é seu turno ou o jogo não começou"

        target_player_id = next(pid for pid in self.players if pid != player_id)
        target_player = self.players[target_player_id]

        if not (
            0 <= target_row < self.board_size and 0 <= target_col < self.board_size
        ):
            return False, "Coordenadas fora do tabuleiro."

        if self.players[player_id]["shots_made"][target_row][target_col] != "~":
            return False, "Já atirou nesta posição"

        hit = target_player["board"][target_row][target_col] == "S"

        if hit:
            target_player["board"][target_row][target_col] = "X"
            self.players[player_id]["shots_made"][target_row][target_col] = "X"
            if self.check_win(target_player["board"]):
                self.game_phase = "game_over"
                self.game_over = True
                return True, "hit_win"
            return True, "hit"
        else:
            self.players[player_id]["shots_made"][target_row][target_col] = "O"
            self.current_turn = target_player_id
            return True, "miss"

    def check_win(self, board):
        return not any("S" in row for row in board)

    def get_game_state(self, player_id):
        if player_id not in self.players:
            return None

        return {
            "your_board": self.players[player_id]["board"],
            "your_shots": self.players[player_id]["shots_made"],
            "current_turn": self.current_turn == player_id,
            "game_phase": self.game_phase,
            "game_over": self.game_over,
            "ships_to_place": self.players[player_id].get("ships_to_place", []),
        }

    def check_all_players_ready(self):
        if len(self.players) < 2:
            return False
        return all(player.get("ready", False) for player in self.players.values())

