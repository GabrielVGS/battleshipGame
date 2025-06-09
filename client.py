import socket
import json
import threading
import time
import os

class BattleshipClient:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.socket = None
        self.player_id = None
        self.game_state = None
        self.running = True
        self.lock = threading.Lock()
        self.connection_established = threading.Event()
        self.placement_update_received = threading.Event()
        self.last_shot_result = ""

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def connect_to_server(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print("Conectado ao servidor!")
            threading.Thread(target=self.listen_to_server, daemon=True).start()
            return True
        except Exception as e:
            print(f"Falha ao conectar ao servidor: {e}")
            return False

    def listen_to_server(self):
        buffer = ""
        while self.running:
            try:
                data = self.socket.recv(4096).decode()
                if not data:
                    self.running = False; break
                buffer += data
                while '\n' in buffer:
                    message_str, buffer = buffer.split('\n', 1)
                    if message_str:
                        message = json.loads(message_str)
                        self.handle_server_message(message)
            except Exception:
                if self.running:
                    print("\nConexão com o servidor perdida.")
                    self.running = False
                break

    def handle_server_message(self, message):
        with self.lock:
            msg_type = message.get('type')

            if msg_type == 'welcome':
                self.player_id = message['player_id']
                if self.game_state is None:
                    self.game_state = {
                        'your_board': [['~'] * 10 for _ in range(10)],
                        'ships_to_place': message.get('ships_to_place', []),
                        'game_phase': 'setup'
                    }
                print(f"\n{message['message']}")
                print("\n=======================================================")
                print(">>> Você está conectado. Configure sua frota. <<<")
                print(">>> Preste atenção nesta janela para as instruções. <<<")
                print("=======================================================")
                self.connection_established.set()
            
            elif msg_type == 'placement_ok':
                self.game_state['your_board'] = message['board']
                self.game_state['ships_to_place'] = message['ships_left']
                self.display_placement_board()
                print(">>> Navio posicionado com sucesso!")
                self.placement_update_received.set()
            
            elif msg_type == 'game_start':
                print(f"\n\n>>> {message['message']} <<<\n")
            
            elif msg_type == 'shot_result':
                result, row, col = message['result'], message['row'], message['col']
                if message['shooter'] == self.player_id:
                    if result == 'hit': self.last_shot_result = f"🎯 ACERTOU! Você atingiu um navio em ({row}, {col})"
                    elif result == 'hit_win': self.last_shot_result = f"🏆 VITÓRIA! Você afundou todos os navios inimigos!"
                    elif result == 'miss': self.last_shot_result = f"💧 ERROU! Nenhum navio em ({row}, {col})"
                else:
                    if result == 'hit': self.last_shot_result = f"💥 ALERTA! Inimigo atingiu seu navio em ({row}, {col})"
                    elif result == 'hit_win': self.last_shot_result = f"💀 DERROTA! Inimigo afundou todos os seus navios!"
                    elif result == 'miss': self.last_shot_result = f"🌊 Sorte! Inimigo errou o tiro em ({row}, {col})"

            elif msg_type == 'game_state':
                self.game_state.update(message['state'])
                if self.game_state['game_phase'] == 'playing':
                    self.display_game_boards()
            
            elif msg_type == 'error':
                print(f"\n❌ Erro do Servidor: {message['message']}")
                if self.game_state.get('game_phase') == 'setup':
                    self.placement_update_received.set()

    def display_placement_board(self):
        self.clear_screen()
        print("="*50); print("      POSICIONE SUA FROTA"); print("="*50)
        self.print_board(self.game_state['your_board'])
        print("\nLegenda: ~ = Água, S = Navio")
    
    def display_game_boards(self):
        if not self.game_state: return
        self.clear_screen()
        

        print(f"\n      BATALHA NAVAL - {self.player_id.upper()}\n")
        print("🚢 SUA FROTA (Ataques Inimigos):")
        self.print_board(self.game_state['your_board'])
        print("\n🎯 SEUS TIROS (Frota Inimiga):")
        self.print_board(self.game_state['your_shots'])
        
        if self.last_shot_result:
            print("\n","="*50)
            print(f">>> {self.last_shot_result} <<<")
            print("="*50)
            # Limpa a mensagem para que não seja exibida novamente
            self.last_shot_result = ""
            
        if self.game_state.get('game_over'):
            print("\n🏁 JOGO TERMINADO!")
        elif self.game_state.get('current_turn'):
            print("\n>>> SUA VEZ! Digite as coordenadas para atirar.")
        else:
            print("\n⏳ Aguardando jogada do oponente...")
        print("\nLegenda: ~ = Água/Desconhecido, S = Navio, X = Acerto, O = Erro")

    def print_board(self, board):
        print("   " + " ".join([f"{i}" for i in range(len(board))]))
        print("  " + "-"*(len(board)*2 + 1))
        for i, row in enumerate(board):
            print(f"{i}| " + " ".join(row))

    def send_message(self, message):
        try: self.socket.send((json.dumps(message) + '\n').encode())
        except Exception as e: self.running = False

    def handle_placement_phase(self):
        choice = ''
        while choice not in ['1', '2']:
            self.clear_screen()
            print("Como você deseja posicionar seus navios?")
            print("1. Automaticamente")
            print("2. Manualmente")
            choice = input(">>> Escolha (1 ou 2): ").strip()
        
        if choice == '1':
            self.send_message({'type': 'placement_choice', 'choice': 'auto'})
        else:
            self.manual_placement_loop()

        print("\nPosicionamento finalizado. Aguardando o outro jogador...")
        while self.running and self.game_state.get('game_phase') == 'setup':
            time.sleep(0.5)

    def manual_placement_loop(self):
        while self.running and self.game_state and self.game_state.get('ships_to_place'):
            self.display_placement_board()
            ship_to_place = self.game_state['ships_to_place'][0]
            print(f"\nPosicione o navio de tamanho {ship_to_place}.")
            
            try:
                coords = input(f">>> Coordenada inicial (linha coluna, ex: '3 4'): ").strip().split()
                row, col = int(coords[0]), int(coords[1])
                direction = ''
                while direction.upper() not in ['H', 'V']:
                    direction = input(">>> Orientação (H para horizontal, V para vertical): ").strip()

                self.placement_update_received.clear()
                self.send_message({'type': 'place_ship', 'length': ship_to_place, 'row': row, 'col': col, 'direction': direction.upper()})
                if not self.placement_update_received.wait(timeout=5):
                    print("O servidor não respondeu. Verifique a conexão.")
            except (ValueError, IndexError):
                print("Entrada inválida. Tente novamente."); time.sleep(2)

    def handle_shooting_phase(self):
        while self.running and self.game_state and not self.game_state.get('game_over'):
            if self.game_state.get('current_turn'):
                try:
                    user_input = input("\n>>> Digite as coordenadas para atirar (linha coluna) ou 'sair': ").strip().lower()
                    if user_input == 'sair': break
                    coords = user_input.split()
                    row, col = int(coords[0]), int(coords[1])
                    if 0 <= row < 10 and 0 <= col < 10:
                        self.send_message({'type': 'shot', 'row': row, 'col': col})
                        with self.lock: self.game_state['current_turn'] = False
                    else: print("Coordenadas devem estar entre 0 e 9.")
                except (ValueError, IndexError): print("Entrada inválida. Use o formato: linha coluna (ex: '3 4')")
            else: time.sleep(0.1)

    def play_game(self):
        if not self.connect_to_server(): return
        if not self.connection_established.wait(timeout=10):
            print("Não foi possível estabelecer a comunicação com o servidor.")
            self.running = False
        else:
            self.handle_placement_phase()
            if self.running: self.handle_shooting_phase()
        self.running = False
        if self.socket: self.socket.close()
        print("\nObrigado por jogar!")

if __name__ == "__main__":
    client = BattleshipClient()
    client.play_game()