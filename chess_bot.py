import discord
from discord.ext import commands
import chess
import chess.svg
import cairosvg
import io
import os
from dotenv import load_dotenv

class ChessGame:
    def __init__(self):
        self.board = chess.Board()
        self.white_player = None
        self.black_player = None
        self.move_history = []  # Now stores only algebraic notation
        
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

class ChessBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='/', intents=intents)
        self.games = {}  # Dictionary to store active games by channel_id
        
    async def setup_hook(self):
        await self.add_cog(ChessCog(self))

class ChessCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.generic_advice = [
            "Have you considered moving the pieces to where they would be more useful?",
            "The key to winning is to not lose.",
            "Try to keep your king alive - it's quite important.",
            "Pieces generally work better when they're not captured.",
            "A knight on d4 is worth two in the starting position.",
            "The best move is usually the one that helps you win.",
            "Remember: pawns can only move backwards in your heart.",
            "If you're losing, try winning instead.",
            "The queen is like a bishop and a rook combined, except when it isn't.",
            "Castle early, castle often (note: you can only castle once).",
            "The best defense is a good offense, unless it's a bad offense.",
            "Try to predict your opponent's moves, or just guess randomly.",
            "Scholars say e4 is best by test, but scholars lose games too.",
            "When in doubt, push pawns randomly.",
            "If your opponent makes a good move, pretend you saw it coming."
        ]
        
        self.piece_types = {
            "pawn": "Consider pushing a pawn to",
            "knight": "Perhaps your knight would enjoy",
            "bishop": "Your bishop seems interested in",
            "rook": "A rook might like",
            "queen": "Your queen could consider",
            "king": "Your king feels drawn to"
        }
        
        self.directions = [
            "the center of the board",
            "the kingside",
            "the queenside",
            "a more aggressive position",
            "a safer square",
            "literally anywhere else",
            "that one square over there",
            "wherever your opponent least expects",
            "the back rank, for dramatic effect",
            "the same place it's already in, but with more confidence",
            "a square of the opposite color",
            "wherever it would look most aesthetically pleasing"
        ]

    @commands.command()
    async def start(self, ctx, fen=None):
        """Start a new chess game, optionally with a FEN position"""
        game = ChessGame()
        if fen:
            try:
                game.board.set_fen(fen)
            except:
                await ctx.send("Invalid FEN position!")
                return
                
        self.bot.games[ctx.channel.id] = game
        await ctx.send("New chess game started!")
        await self.send_board(ctx)

    @commands.command()
    async def move(self, ctx, move_str: str):
        """Make a move using algebraic notation (e.g., /move e4) or UCI notation (e.g., /move e2e4)"""
        game = self.bot.games.get(ctx.channel.id)
        if not game:
            await ctx.send("No active game in this channel!")
            return
            
        if game.make_move(move_str):
            await ctx.send(f"Move {move_str} played!")
            await self.send_board(ctx)
        else:
            await ctx.send("Invalid move!")

    @commands.command()
    async def undo(self, ctx):
        """Undo the last move"""
        game = self.bot.games.get(ctx.channel.id)
        if not game:
            await ctx.send("No active game in this channel!")
            return
            
        move = game.undo_move()
        if move:
            await ctx.send(f"Move {move} undone!")
            await self.send_board(ctx)
        else:
            await ctx.send("No moves to undo!")

    @commands.command()
    async def history(self, ctx):
        """Show the move history in algebraic notation"""
        game = self.bot.games.get(ctx.channel.id)
        if not game:
            await ctx.send("No active game in this channel!")
            return
            
        if not game.move_history:
            await ctx.send("No moves played yet!")
            return
            
        # Format moves with numbers
        formatted_moves = []
        for i, move in enumerate(game.move_history):
            if i % 2 == 0:
                formatted_moves.append(f"{i//2 + 1}. {move}")
            else:
                formatted_moves.append(move)
                
        moves = " ".join(formatted_moves)
        await ctx.send(f"Move history: {moves}")

    @commands.command()
    async def teams(self, ctx):
        """Show current teams"""
        game = self.bot.games.get(ctx.channel.id)
        if not game:
            await ctx.send("No active game in this channel!")
            return
            
        white = game.white_player.name if game.white_player else "Vacant"
        black = game.black_player.name if game.black_player else "Vacant"
        await ctx.send(f"White: {white}\nBlack: {black}")

    @commands.command()
    async def join(self, ctx, color: str):
        """Join as either 'white' or 'black'"""
        game = self.bot.games.get(ctx.channel.id)
        if not game:
            await ctx.send("No active game in this channel!")
            return
            
        color = color.lower()
        if color not in ['white', 'black']:
            await ctx.send("Please specify 'white' or 'black'!")
            return
            
        if color == 'white':
            game.white_player = ctx.author
            await ctx.send(f"{ctx.author.name} is now playing as White!")
        else:
            game.black_player = ctx.author
            await ctx.send(f"{ctx.author.name} is now playing as Black!")

    async def send_board(self, ctx):
        """Helper function to send the current board state"""
        game = self.bot.games.get(ctx.channel.id)
        if game:
            board_image = game.get_board_image()
            await ctx.send(file=discord.File(board_image, 'board.png'))

    @commands.command()
    async def advice(self, ctx):
        """Get some questionably useful chess advice"""
        import random
        
        if random.random() < 0.3:
            advice = random.choice(self.generic_advice)
        else:
            piece = random.choice(list(self.piece_types.keys()))
            direction = random.choice(self.directions)
            advice = f"{self.piece_types[piece]} {direction}."
        await ctx.send(f"🧙‍♂️ Chess Wisdom: {advice}")


if __name__ == "__main__":
    load_dotenv()
    bot = ChessBot()
    bot.run(os.getenv('DISCORD_TOKEN'))