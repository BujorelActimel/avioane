import socket
import pickle
from collections import defaultdict
import signal
import sys
import threading

class GameServer:
    def __init__(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Set a timeout on the socket so accept() doesn't block forever
        self.server.settimeout(1.0)
        
        self.server.bind(('localhost', 5555))
        self.server.listen(2)
        print("Server started, waiting for connections...")
        
        self.games = {}
        self.players = {}
        self.grids = {}
        self.shots = defaultdict(list)
        self.head_positions = defaultdict(list)
        self.heads_hit = defaultdict(int)
        self.current_player = "1"
        self.placement_phase = True
        self.running = True
        
        # Set up signal handler
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def signal_handler(self, sig, frame):
        print("\nShutting down server...")
        self.shutdown()
        sys.exit(0)
        
    def shutdown(self):
        self.running = False
        # Close all client connections
        for conn in self.players.values():
            try:
                conn.close()
            except:
                pass
        # Close server socket
        try:
            self.server.close()
        except:
            pass
        
    def handle_client(self, conn, player_id):
        while self.running:
            try:
                data = pickle.loads(conn.recv(4096))
                if not data:
                    break

                # Update server state
                self.grids[player_id] = data["grid"]
                if "head_positions" in data:
                    self.head_positions[player_id] = data["head_positions"]
                    
                opponent_id = "2" if player_id == "1" else "1"
                current_shots = data.get("shots", [])
                
                shot_results = {}
                # Process new shots
                for row in range(len(current_shots)):
                    for col in range(len(current_shots[row])):
                        if current_shots[row][col] and (row, col) not in self.shots[player_id]:
                            self.shots[player_id].append((row, col))
                            # Check if it's a head shot
                            if (row, col) in self.head_positions[opponent_id]:
                                shot_results[(row, col)] = "head"
                                self.heads_hit[player_id] += 1
                            # Check if it's a body shot
                            elif opponent_id in self.grids and self.grids[opponent_id][row][col] != (255, 255, 255):
                                shot_results[(row, col)] = "hit"
                            else:
                                shot_results[(row, col)] = "miss"

                # Check if placement phase is complete
                if self.placement_phase:
                    if len(self.grids) == 2:
                        planes_placed_p1 = len(self.head_positions["1"])
                        planes_placed_p2 = len(self.head_positions["2"])
                        if planes_placed_p1 >= 3 and planes_placed_p2 >= 3:
                            self.placement_phase = False
                            print("Placement phase complete, starting game")

                # Prepare response
                response = {
                    "opponent_ready": len(self.grids) == 2,
                    "your_turn": self.current_player == player_id,
                    "placement_phase": self.placement_phase,
                    "opponent_shots": self.shots[opponent_id],
                    "heads_hit": self.heads_hit[player_id],
                    "opponent_heads_hit": self.heads_hit[opponent_id],
                    "shot_results": shot_results
                }

                # Switch turns if a shot was made
                if shot_results and not self.placement_phase:
                    self.current_player = opponent_id

                conn.send(pickle.dumps(response))
                
            except Exception as e:
                print(f"Error handling client {player_id}:", e)
                break
                
        print(f"Client {player_id} disconnected")
        if player_id in self.players:
            del self.players[player_id]
        conn.close()

    def run(self):
        while self.running:
            try:
                conn, addr = self.server.accept()
                player_id = str(len(self.players) + 1)
                print(f"Player {player_id} connected from {addr}")
                
                conn.send(str.encode(player_id))
                self.players[player_id] = conn
                
                # Start a new thread for this client
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(conn, player_id)
                )
                client_thread.daemon = True
                client_thread.start()
                
                if len(self.players) > 2:
                    print("Extra player tried to connect")
                    conn.close()
                
            except socket.timeout:
                # This allows checking the running flag periodically
                continue
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error accepting connection: {e}")
                if not self.running:
                    break

if __name__ == "__main__":
    server = GameServer()
    try:
        server.run()
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt, shutting down...")
        server.shutdown()