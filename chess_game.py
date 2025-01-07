import chess
import io
import cairosvg

class ChessGame:
    def __init__(self):
        self.board = chess.Board()
        self.white_player = None
        self.black_player = None
        self.move_history = []
        self.completed = False  # New flag to mark if game is finished
        self.timestamp = None  # When the game was started/completed
        
    def to_dict(self):
        """Convert game state to dictionary for saving"""
        return {
            'fen': self.board.fen(),
            'white_player': self.white_player.id if self.white_player else None,
            'black_player': self.black_player.id if self.black_player else None,
            'move_history': self.move_history,
            'completed': self.completed,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data, bot):
        """Create a game instance from saved dictionary"""
        game = cls()
        game.board.set_fen(data['fen'])
        game.move_history = data['move_history']
        game.completed = data.get('completed', False)  # Default to False for backward compatibility
        game.timestamp = data.get('timestamp')
        
        # Restore player objects from IDs
        if data['white_player']:
            game.white_player = bot.get_user(data['white_player'])
        if data['black_player']:
            game.black_player = bot.get_user(data['black_player'])
        
        return game

    def make_move(self, move_str):
        try:
            # Try parsing as algebraic notation first
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
                    self.move_history.append(san)  # Store as algebraic notation
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
        svg_data = chess.svg.board(self.board)
        
        png_data = io.BytesIO()
        cairosvg.svg2png(bytestring=svg_data.encode('utf-8'), write_to=png_data)
        png_data.seek(0)
        return png_data