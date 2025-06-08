import socket
import json
import threading
import time

class BattleshipClient:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.socket = None
        self.player_id = None
        self.game_state = None
        self.running = True
        
    def connect_to_server(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print("Connected to server!")
            
            # Start listening thread
            threading.Thread(target=self.listen_to_server, daemon=True).start()
            
            return True
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            return False
    
    def listen_to_server(self):
        while self.running:
            try:
                data = self.socket.recv(2048).decode()
                if not data:
                    break
                
                message = json.loads(data)
                self.handle_server_message(message)
                
            except Exception as e:
                if self.running:
                    print(f"Error receiving data: {e}")
                break
    
    def handle_server_message(self, message):
        msg_type = message['type']
        
        if msg_type == 'welcome':
            self.player_id = message['player_id']
            print(f"\n{message['message']}")
            print("Waiting for another player to join...")
            
        elif msg_type == 'game_start':
            print(f"\n{message['message']}")
            
        elif msg_type == 'game_state':
            self.game_state = message['state']
            self.display_game_state()
            
        elif msg_type == 'shot_result':
            result = message['result']
            row, col = message['row'], message['col']
            shooter = message['shooter']
            
            if shooter == self.player_id:
                if result == 'hit':
                    print(f"\n🎯 HIT! You hit the enemy ship at ({row}, {col})")
                elif result == 'hit_win':
                    print(f"\n🏆 GAME WON! You sank all enemy ships!")
                elif result == 'miss':
                    print(f"\n💧 MISS! No ship at ({row}, {col})")
            else:
                if result == 'hit':
                    print(f"\n💥 Enemy hit your ship at ({row}, {col})")
                elif result == 'hit_win':
                    print(f"\n💀 GAME OVER! Enemy sank all your ships!")
                elif result == 'miss':
                    print(f"\n🌊 Enemy missed at ({row}, {col})")
            
        elif msg_type == 'error':
            print(f"\n❌ Error: {message['message']}")
    
    def display_game_state(self):
        if not self.game_state:
            return
        
        print("\n" + "="*50)
        print(f"BATTLESHIP GAME - {self.player_id.upper()}")
        print("="*50)
        
        print("\n🚢 YOUR FLEET:")
        self.print_board(self.game_state['your_board'], show_ships=True)
        
        print("\n🎯 YOUR SHOTS:")
        self.print_board(self.game_state['your_shots'], show_ships=False)
        
        print("\n💥 ENEMY HITS ON YOU:")
        self.print_board(self.game_state['opponent_shots'], show_ships=False)
        
        if self.game_state['game_over']:
            print("\n🏁 GAME OVER!")
        elif self.game_state['current_turn']:
            print("\n🎯 YOUR TURN! Enter coordinates to shoot.")
        else:
            print("\n⏳ Waiting for opponent's move...")
        
        print("\nLegend: ~ = Water, S = Ship, X = Hit, O = Miss")
    
    def print_board(self, board, show_ships=True):
        print("   " + " ".join([str(i) for i in range(10)]))
        for i, row in enumerate(board):
            row_str = f"{i}: "
            for cell in row:
                if cell == 'S' and not show_ships:
                    row_str += "~ "
                else:
                    row_str += f"{cell} "
            print(row_str)
    
    def make_shot(self, row, col):
        shot_msg = {
            'type': 'shot',
            'row': row,
            'col': col
        }
        try:
            self.socket.send(json.dumps(shot_msg).encode())
        except Exception as e:
            print(f"Error sending shot: {e}")
    
    def play_game(self):
        if not self.connect_to_server():
            return
        
        print("Welcome to Battleship!")
        print("Ships have been automatically placed for you.")
        print("Enter coordinates as 'row col' (e.g., '3 4') to shoot.")
        print("Type 'quit' to exit the game.")
        
        while self.running:
            try:
                if (self.game_state and 
                    self.game_state['game_started'] and 
                    self.game_state['current_turn'] and 
                    not self.game_state['game_over']):
                    
                    user_input = input("\nEnter coordinates (row col): ").strip().lower()
                    
                    if user_input == 'quit':
                        break
                    
                    try:
                        row, col = map(int, user_input.split())
                        if 0 <= row < 10 and 0 <= col < 10:
                            self.make_shot(row, col)
                        else:
                            print("Coordinates must be between 0-9")
                    except ValueError:
                        print("Invalid input. Use format: row col (e.g., '3 4')")
                
                elif self.game_state and self.game_state['game_over']:
                    play_again = input("\nGame over! Type 'quit' to exit: ").strip().lower()
                    if play_again == 'quit':
                        break
                
                else:
                    time.sleep(0.1)  # Small delay to prevent busy waiting
                    
            except KeyboardInterrupt:
                break
            except EOFError:
                break
        
        self.running = False
        if self.socket:
            self.socket.close()
        print("\nThanks for playing!")

if __name__ == "__main__":
    client = BattleshipClient()
    client.play_game()