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


class BattleshipServer:
    def __init__(self, host="localhost", port=12345):
        self.host = host
        self.port = port
        self.game = BattleshipGame()
        self.clients = {}
        self.lock = threading.Lock()

    def start_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(2)

        print(f"Servidor Batalha Naval iniciado em {self.host}:{self.port}")
        print("Aguardando jogadores...")

        while len(self.clients) < 2:
            client_socket, addr = server_socket.accept()
            player_id = f"player_{len(self.clients) + 1}"

            self.clients[player_id] = client_socket
            self.game.players[player_id] = {
                "board": self.game.create_empty_board(),
                "shots_made": self.game.create_empty_board(),
                "ready": False,
                "ships_to_place": list(self.game.ships),
            }

            print(f"Jogador {player_id} conectado de {addr}.")

            welcome_msg = {
                "type": "welcome",
                "player_id": player_id,
                "message": f"Bem-vindo! Você é o {player_id}",
                "ships_to_place": self.game.ships,
            }
            client_socket.send((json.dumps(welcome_msg) + "\n").encode())

            threading.Thread(
                target=self.handle_client, args=(client_socket, player_id)
            ).start()

        print("Dois jogadores conectados. Fase de posicionamento iniciada.")
        print("Servidor: Aguardando ambos os jogadores finalizarem o posicionamento...")

    def handle_client(self, client_socket, player_id):
        while True:
            try:
                data = client_socket.recv(4096).decode()
                if not data:
                    break

                messages = data.strip().split("\n")
                for msg_str in messages:
                    if not msg_str:
                        continue
                    message = json.loads(msg_str)
                    self.process_message(message, player_id)

            except Exception:
                break

        with self.lock:
            print(f"Jogador {player_id} desconectado.")
            client_socket.close()
            if player_id in self.clients:
                del self.clients[player_id]
            if player_id in self.game.players:
                del self.game.players[player_id]

            if self.game.game_phase != "setup" and len(self.clients) > 0:
                error_msg = {
                    "type": "error",
                    "message": "O oponente desconectou. O jogo terminou.",
                }
                self.broadcast_message(error_msg)
                self.game.game_phase = "game_over"
                self.game.game_over = True
                self.send_game_state_to_all()

    def process_message(self, message, player_id):
        with self.lock:
            msg_type = message.get("type")

            if self.game.game_phase == "setup":
                player_ready = False
                if msg_type == "placement_choice" and message["choice"] == "auto":
                    player_board = self.game.players[player_id]["board"]
                    self.game.auto_place_ships(player_board)
                    self.game.players[player_id]["ships_to_place"] = []
                    player_ready = True
                    print(f"Servidor: {player_id} escolheu posicionamento automático.")
                    self.send_game_state_to_all()

                elif msg_type == "place_ship":
                    player = self.game.players[player_id]
                    if self.game.is_valid_placement(
                        player["board"],
                        message["row"],
                        message["col"],
                        message["length"],
                        message["direction"],
                    ):
                        self.game.place_ship(
                            player["board"],
                            message["row"],
                            message["col"],
                            message["length"],
                            message["direction"],
                        )
                        player["ships_to_place"].remove(message["length"])

                        self.clients[player_id].send(
                            (
                                json.dumps(
                                    {
                                        "type": "placement_ok",
                                        "board": player["board"],
                                        "ships_left": player["ships_to_place"],
                                    }
                                )
                                + "\n"
                            ).encode()
                        )

                        if not player["ships_to_place"]:
                            player_ready = True
                            print(
                                f"Servidor: {player_id} finalizou o posicionamento manual."
                            )
                    else:
                        self.send_error(
                            player_id, "Posicionamento inválido. Tente novamente."
                        )

                if player_ready:
                    self.game.players[player_id]["ready"] = True
                    if self.game.check_all_players_ready():
                        self.start_game()
                    else:
                        print(
                            f"Servidor: {player_id} está pronto. Aguardando o outro jogador."
                        )

            elif self.game.game_phase == "playing":
                if msg_type == "shot":
                    success, result = self.game.make_shot(
                        player_id, message["row"], message["col"]
                    )
                    if success:
                        self.broadcast_message(
                            {
                                "type": "shot_result",
                                "result": result,
                                "row": message["row"],
                                "col": message["col"],
                                "shooter": player_id,
                            }
                        )
                        self.send_game_state_to_all()
                    else:
                        self.send_error(player_id, result)

    def start_game(self):
        self.game.game_phase = "playing"
        self.game.current_turn = "player_1"
        print(
            "Servidor: Ambos os jogadores estão prontos! Jogo iniciado. Vez do player_1."
        )
        self.broadcast_message(
            {
                "type": "game_start",
                "message": "Todos os jogadores estão prontos! Jogo iniciado. Jogador 1 começa.",
            }
        )
        self.send_game_state_to_all()

    def broadcast_message(self, message):
        msg_json = json.dumps(message) + "\n"
        for client_socket in list(self.clients.values()):
            try:
                client_socket.send(msg_json.encode())
            except:
                pass

    def send_game_state_to_all(self):
        for player_id in list(self.clients.keys()):
            if player_id in self.clients:
                game_state = self.game.get_game_state(player_id)
                if game_state:
                    message = {"type": "game_state", "state": game_state}
                    try:
                        self.clients[player_id].send(
                            (json.dumps(message) + "\n").encode()
                        )
                    except:
                        pass

    def send_error(self, player_id, error_message):
        error_msg = {"type": "error", "message": error_message}
        if player_id in self.clients:
            try:
                self.clients[player_id].send((json.dumps(error_msg) + "\n").encode())
            except:
                pass


if __name__ == "__main__":
    server = BattleshipServer()
    server.start_server()
