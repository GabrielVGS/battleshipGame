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
            print("Conectado ao servidor!")
            
            # Start listening thread
            threading.Thread(target=self.listen_to_server, daemon=True).start()
            
            return True
        except Exception as e:
            print(f"Falha ao conectar ao servidor: {e}")
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
                    print(f"Erro ao receber dados: {e}")
                break
    
    def handle_server_message(self, message):
        msg_type = message['type']
        
        if msg_type == 'welcome':
            self.player_id = message['player_id']
            print(f"\n{message['message']}")
            print("Aguardando outro jogador se juntar...")
            
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
                    print(f"\n🎯 ACERTOU! Você atingiu o navio inimigo em ({row}, {col})")
                elif result == 'hit_win':
                    print(f"\n🏆 VITÓRIA! Você afundou todos os navios inimigos!")
                elif result == 'miss':
                    print(f"\n💧 ERROU! Nenhum navio em ({row}, {col})")
            else:
                if result == 'hit':
                    print(f"\n💥 Inimigo atingiu seu navio em ({row}, {col})")
                elif result == 'hit_win':
                    print(f"\n💀 DERROTA! Inimigo afundou todos os seus navios!")
                elif result == 'miss':
                    print(f"\n🌊 Inimigo errou em ({row}, {col})")
            
        elif msg_type == 'error':
            print(f"\n❌ Erro: {message['message']}")
    
    def display_game_state(self):
        if not self.game_state:
            return
        
        print("\n" + "="*50)
        print(f"BATALHA NAVAL - {self.player_id.upper()}")
        print("="*50)
        
        print("\n🚢 SUA FROTA:")
        self.print_board(self.game_state['your_board'], show_ships=True)
        
        print("\n🎯 SEUS TIROS:")
        self.print_board(self.game_state['your_shots'], show_ships=False)
        
        print("\n💥 ATAQUES INIMIGOS EM VOCÊ:")
        self.print_board(self.game_state['opponent_shots'], show_ships=False)
        
        if self.game_state['game_over']:
            print("\n🏁 JOGO TERMINADO!")
        elif self.game_state['current_turn']:
            print("\n🎯 SUA VEZ! Digite as coordenadas para atirar.")
        else:
            print("\n⏳ Aguardando jogada do oponente...")
        
        print("\nLegenda: ~ = Água, S = Navio, X = Acerto, O = Erro")
    
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
            print(f"Erro ao enviar tiro: {e}")
    
    def play_game(self):
        if not self.connect_to_server():
            return
        
        print("Bem-vindo à Batalha Naval!")
        print("Os navios foram posicionados automaticamente para você.")
        print("Digite as coordenadas como 'linha coluna' (ex: '3 4') para atirar.")
        print("Digite 'sair' para sair do jogo.")
        
        while self.running:
            try:
                if (self.game_state and 
                    self.game_state['game_started'] and 
                    self.game_state['current_turn'] and 
                    not self.game_state['game_over']):
                    
                    user_input = input("\nDigite as coordenadas (linha coluna): ").strip().lower()
                    
                    if user_input == 'sair':
                        break
                    
                    try:
                        row, col = map(int, user_input.split())
                        if 0 <= row < 10 and 0 <= col < 10:
                            self.make_shot(row, col)
                        else:
                            print("Coordenadas devem estar entre 0-9")
                    except ValueError:
                        print("Entrada inválida. Use o formato: linha coluna (ex: '3 4')")
                
                elif self.game_state and self.game_state['game_over']:
                    play_again = input("\nJogo terminado! Digite 'sair' para sair: ").strip().lower()
                    if play_again == 'sair':
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
        print("\nObrigado por jogar!")

if __name__ == "__main__":
    client = BattleshipClient()
    client.play_game()