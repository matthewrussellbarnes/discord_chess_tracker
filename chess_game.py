import chess
import chess.svg
import io
import cairosvg
import random

class ChessGame:
    def __init__(self, variant_960=False):
        if variant_960:
            # Generate random Chess960 starting position
            self.board = chess.Board.from_chess960_pos(random.randint(0, 959))
            # Set initial castling rights for both sides
            self.reset_castling_rights(chess.WHITE, "kingside")
            self.reset_castling_rights(chess.WHITE, "queenside")
            self.reset_castling_rights(chess.BLACK, "kingside")
            self.reset_castling_rights(chess.BLACK, "queenside")
        else:
            self.board = chess.Board()
        self.white_players = []  # List of players on white team
        self.black_players = []  # List of players on black team
        self.move_history = []
        self.completed = False
        self.timestamp = None
        self.is_960 = variant_960  # Store if this is a Chess960 game
        self.starting_fen = self.board.fen()  # Store the starting position
        self.white_player_ids = []  # Add this
        self.black_player_ids = []  # Add this

    def to_dict(self):
        """Convert game state to dictionary for saving"""
        return {
            'fen': self.board.fen(),
            'starting_fen': self.starting_fen,  # Save the starting position
            'white_players': [player.id for player in self.white_players],
            'black_players': [player.id for player in self.black_players],
            'move_history': self.move_history,
            'completed': self.completed,
            'timestamp': self.timestamp,
            'is_960': self.is_960
        }
    
    @classmethod
    def from_dict(cls, data, bot):
        """Create a game instance from saved dictionary"""
        game = cls(variant_960=data.get('is_960', False))
        
        game.board.set_fen(data['fen'])
        game.starting_fen = data.get('starting_fen', chess.Board().fen())  # Load starting position with fallback
        game.move_history = data['move_history']
        game.completed = data.get('completed', False)
        game.timestamp = data.get('timestamp')
        game.is_960 = data.get('is_960', False)
        
        game.white_players = [bot.get_user(pid) for pid in data['white_players'] if bot.get_user(pid)]
        game.black_players = [bot.get_user(pid) for pid in data['black_players'] if bot.get_user(pid)]
        
        return game
        
    def make_move(self, move_str):
        try:
            if 'o' in move_str.lower():
                move_str = move_str.upper().replace('0', 'O')
            move = self.board.parse_san(move_str)
            self.board.push(move)
            self.move_history.append(move_str)
            return True
        except ValueError:
            try:
                # Fallback to UCI notation if algebraic fails
                move = chess.Move.from_uci(move_str)
                if move in self.board.legal_moves:
                    # Get the SAN before pushing the move
                    san = self.board.san(move)
                    self.board.push(move)
                    self.move_history.append(san)
                    return True
            except:
                pass
            return False
            
    def undo_move(self):
        if len(self.move_history) > 0:
            self.board.pop()
            return self.move_history.pop()
        return None
        
    def get_board_image(self):
        """Convert board to SVG then to PNG"""
        svg_data = chess.svg.board(self.board)
        png_data = cairosvg.svg2png(bytestring=svg_data.encode('utf-8'))
        return io.BytesIO(png_data)
        
    def get_current_status(self):
        """Get the current game status as a formatted string"""
        # Get player names
        white = ", ".join(p.name for p in self.white_players) if self.white_players else "Vacant"
        black = ", ".join(p.name for p in self.black_players) if self.black_players else "Vacant"
        
        # Determine whose turn it is
        current_turn = "White" if self.board.turn == chess.WHITE else "Black"
        current_players = self.white_players if self.board.turn == chess.WHITE else self.black_players
        player_names = ", ".join(p.name for p in current_players) if current_players else "No players"
        
        return [
            f"⚪ White: {white}",
            f"⚫ Black: {black}",
            f"\nTurn {len(self.move_history) // 2 + 1}",
            f"It's {current_turn}'s turn ({player_names})"
        ]
    
    def get_next_turn_text(self):
        """Get text indicating whose turn is next"""
        next_turn = "White" if self.board.turn == chess.WHITE else "Black"
        next_players = self.white_players if self.board.turn == chess.WHITE else self.black_players
        if next_players:
            player_names = ", ".join(p.name for p in next_players)
            return f"It's {next_turn}'s turn ({player_names})"
        return f"It's {next_turn}'s turn (no players assigned)"

    def reset_castling_rights(self, color, wing):
        """Reset castling rights for a specific color and wing"""
        rank = chess.BB_RANK_1 if color == chess.WHITE else chess.BB_RANK_8
        rooks = self.board.rooks & rank & self.board.occupied_co[color]
        
        if wing == "kingside":
            rook_square = chess.BB_SQUARES[chess.msb(rooks)]  # rightmost rook
            self.board.castling_rights |= rook_square
        elif wing == "queenside":
            rook_square = chess.BB_SQUARES[chess.lsb(rooks)]  # leftmost rook
            self.board.castling_rights |= rook_square

    def get_castling_rights(self):
        """Get a human-readable description of current castling rights"""
        rights = []
        
        # Check White's castling rights
        if self.board.has_kingside_castling_rights(chess.WHITE):
            rights.append("White O-O")
        if self.board.has_queenside_castling_rights(chess.WHITE):
            rights.append("White O-O-O")
        
        # Check Black's castling rights
        if self.board.has_kingside_castling_rights(chess.BLACK):
            rights.append("Black O-O")
        if self.board.has_queenside_castling_rights(chess.BLACK):
            rights.append("Black O-O-O")
        
        if not rights:
            return "No castling rights remaining"
        
        return "Available castling: " + ", ".join(rights)