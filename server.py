import socket
import threading
import json
import random

class BattleshipGame:
    def __init__(self):
        self.board_size = 10
        self.ships = [5, 4, 3, 3, 2]  # Ship lengths
        self.players = {}
        self.current_turn = None
        self.game_started = False
        self.game_over = False
        
    def create_empty_board(self):
        return [['~' for _ in range(self.board_size)] for _ in range(self.board_size)]
    
    def is_valid_placement(self, board, row, col, length, direction):
        if direction == 'H':  # Horizontal
            if col + length > self.board_size:
                return False
            for c in range(col, col + length):
                if board[row][c] != '~':
                    return False
        else:  # Vertical
            if row + length > self.board_size:
                return False
            for r in range(row, row + length):
                if board[r][col] != '~':
                    return False
        return True
    
    def place_ship(self, board, row, col, length, direction):
        if direction == 'H':
            for c in range(col, col + length):
                board[row][c] = 'S'
        else:
            for r in range(row, row + length):
                board[r][col] = 'S'
    
    def auto_place_ships(self, board):
        for ship_length in self.ships:
            placed = False
            attempts = 0
            while not placed and attempts < 100:
                row = random.randint(0, self.board_size - 1)
                col = random.randint(0, self.board_size - 1)
                direction = random.choice(['H', 'V'])
                
                if self.is_valid_placement(board, row, col, ship_length, direction):
                    self.place_ship(board, row, col, ship_length, direction)
                    placed = True
                attempts += 1
    
    def make_shot(self, player_id, target_row, target_col):
        if self.current_turn != player_id or self.game_over:
            return False, "Not your turn or game is over"
        
        target_player = None
        for pid, player in self.players.items():
            if pid != player_id:
                target_player = player
                break
        
        if not target_player:
            return False, "No opponent found"
        
        # Check if already shot at this position
        if target_player['shots_received'][target_row][target_col] != '~':
            return False, "Already shot at this position"
        
        # Check if hit
        hit = target_player['board'][target_row][target_col] == 'S'
        
        if hit:
            target_player['shots_received'][target_row][target_col] = 'X'
            target_player['board'][target_row][target_col] = 'X'
            # Check if all ships are sunk
            if self.check_win(target_player['board']):
                self.game_over = True
                return True, "hit_win"
            return True, "hit"
        else:
            target_player['shots_received'][target_row][target_col] = 'O'
            # Switch turns
            self.current_turn = list(self.players.keys())[0] if self.current_turn == list(self.players.keys())[1] else list(self.players.keys())[1]
            return True, "miss"
    
    def check_win(self, board):
        for row in board:
            for cell in row:
                if cell == 'S':
                    return False
        return True
    
    def get_game_state(self, player_id):
        if player_id not in self.players:
            return None
        
        opponent_id = None
        for pid in self.players:
            if pid != player_id:
                opponent_id = pid
                break
        
        return {
            'your_board': self.players[player_id]['board'],
            'your_shots': self.players[player_id]['shots_made'],
            'opponent_shots': self.players[player_id]['shots_received'],
            'current_turn': self.current_turn == player_id,
            'game_started': self.game_started,
            'game_over': self.game_over
        }

class BattleshipServer:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.game = BattleshipGame()
        self.clients = {}
        
    def start_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(2)
        
        print(f"Battleship server started on {self.host}:{self.port}")
        print("Waiting for players...")
        
        while len(self.clients) < 2:
            client_socket, addr = server_socket.accept()
            player_id = f"player_{len(self.clients) + 1}"
            
            self.clients[player_id] = client_socket
            self.game.players[player_id] = {
                'board': self.game.create_empty_board(),
                'shots_made': self.game.create_empty_board(),
                'shots_received': self.game.create_empty_board()
            }
            
            print(f"Player {len(self.clients)} connected from {addr}")
            
            # Auto-place ships for this player
            self.game.auto_place_ships(self.game.players[player_id]['board'])
            
            # Send welcome message
            welcome_msg = {
                'type': 'welcome',
                'player_id': player_id,
                'message': f'Welcome! You are {player_id}'
            }
            client_socket.send(json.dumps(welcome_msg).encode())
            
            # Start client handler thread
            threading.Thread(target=self.handle_client, args=(client_socket, player_id)).start()
        
        # Start the game when both players are connected
        self.game.game_started = True
        self.game.current_turn = 'player_1'
        
        # Notify both players that the game has started
        start_msg = {
            'type': 'game_start',
            'message': 'Game started! Player 1 goes first.'
        }
        self.broadcast_message(start_msg)
        
        # Send initial game state to both players
        self.send_game_state_to_all()
        
    def handle_client(self, client_socket, player_id):
        while True:
            try:
                data = client_socket.recv(2048).decode()
                if not data:
                    break
                
                message = json.loads(data)
                self.process_message(message, player_id)
                
            except Exception as e:
                print(f"Error handling client {player_id}: {e}")
                break
        
        client_socket.close()
        del self.clients[player_id]
        del self.game.players[player_id]
    
    def process_message(self, message, player_id):
        if message['type'] == 'shot':
            row, col = message['row'], message['col']
            success, result = self.game.make_shot(player_id, row, col)
            
            if success:
                # Update the shooting player's shots_made board
                target_player = None
                for pid, player in self.game.players.items():
                    if pid != player_id:
                        target_player = player
                        break
                
                if result == "hit" or result == "hit_win":
                    self.game.players[player_id]['shots_made'][row][col] = 'X'
                else:
                    self.game.players[player_id]['shots_made'][row][col] = 'O'
                
                # Send shot result
                shot_result = {
                    'type': 'shot_result',
                    'result': result,
                    'row': row,
                    'col': col,
                    'shooter': player_id
                }
                self.broadcast_message(shot_result)
                
                # Send updated game state
                self.send_game_state_to_all()
                
            else:
                error_msg = {
                    'type': 'error',
                    'message': result
                }
                self.clients[player_id].send(json.dumps(error_msg).encode())
    
    def broadcast_message(self, message):
        for client_socket in self.clients.values():
            try:
                client_socket.send(json.dumps(message).encode())
            except:
                pass
    
    def send_game_state_to_all(self):
        for player_id in self.clients:
            game_state = self.game.get_game_state(player_id)
            if game_state:
                message = {
                    'type': 'game_state',
                    'state': game_state
                }
                try:
                    self.clients[player_id].send(json.dumps(message).encode())
                except:
                    pass

if __name__ == "__main__":
    server = BattleshipServer()
    server.start_server()