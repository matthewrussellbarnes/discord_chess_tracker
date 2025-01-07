import discord
from discord.ext import commands
import chess
import datetime
import chess.svg
from chess_game import ChessGame

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
        channel_id = ctx.channel.id
        
        # Check if there's already an active game
        if channel_id in self.bot.channel_data and self.bot.channel_data[channel_id].get('current_game'):
            await ctx.send("There's already an active game! Use `/stop` to end it first.")
            return
        
        game = ChessGame()
        game.timestamp = datetime.datetime.now().isoformat()
        if fen:
            try:
                game.board.set_fen(fen)
            except:
                await ctx.send("Invalid FEN position!")
                return
        
        if channel_id not in self.bot.channel_data:
            self.bot.channel_data[channel_id] = {
                'current_game': None,
                'past_games': []
            }
        
        self.bot.channel_data[channel_id]['current_game'] = game
        await ctx.send("New chess game started!")
        await self.send_board(ctx)
        self.bot.save_games()

    @commands.command()
    async def stop(self, ctx):
        """Stop the current game and save it to history"""
        channel_id = ctx.channel.id
        
        if channel_id not in self.bot.channel_data or not self.bot.channel_data[channel_id].get('current_game'):
            await ctx.send("No active game to stop!")
            return
        
        # Archive the current game
        current_game = self.bot.channel_data[channel_id]['current_game']
        current_game.completed = True
        current_game.timestamp = datetime.datetime.now().isoformat()
        
        if 'past_games' not in self.bot.channel_data[channel_id]:
            self.bot.channel_data[channel_id]['past_games'] = []
        
        self.bot.channel_data[channel_id]['past_games'].append(current_game)
        self.bot.channel_data[channel_id]['current_game'] = None
        
        await ctx.send("Game stopped and saved to history!")
        self.bot.save_games()

    @commands.command(name='current')
    async def show_current(self, ctx):
        """Show the current game status"""
        game = self.bot.get_current_game(ctx.channel.id)
        if not game:
            await ctx.send("No active game in this channel!")
            return
        
        status = game.get_current_status()
        await ctx.send("\n".join(status))
        await self.send_board(ctx)

    @commands.command()
    async def move(self, ctx, move_str: str):
        """Make a move using algebraic notation (e.g., /move e4)"""
        game = self.bot.get_current_game(ctx.channel.id)
        if not game:
            await ctx.send("No active game in this channel!")
            return
            
        if game.make_move(move_str):
            await ctx.send(f"Move {move_str} played!")
            await self.send_board(ctx)
            
            # Check for checkmate or stalemate
            if game.board.is_checkmate():
                winner = "Black" if game.board.turn == chess.WHITE else "White"
                await ctx.send(f"Checkmate! {winner} wins! 🎉")
                await self.stop(ctx)
            elif game.board.is_stalemate():
                await ctx.send("Stalemate! The game is a draw! 🤝")
                await self.stop(ctx)
            else:
                await ctx.send(game.get_next_turn_text())
            
            self.bot.save_games()
        else:
            await ctx.send("Invalid move!")

    @commands.command()
    async def undo(self, ctx):
        """Undo the last move"""
        game = self.bot.get_current_game(ctx.channel.id)
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
    async def history(self, ctx, game_number: int = None):
        """Show move history. Use a number to see a past game."""
        channel_id = ctx.channel.id
        if channel_id not in self.bot.channel_data:
            await ctx.send("No games have been played in this channel!")
            return
            
        channel_data = self.bot.channel_data[channel_id]
        
        if game_number is not None:
            # Show past game
            past_games = channel_data.get('past_games', [])
            if not past_games:
                await ctx.send("No past games found!")
                return
                
            try:
                game = past_games[game_number - 1]  # Convert to 0-based index
                response = [f"Game #{game_number} - {game.timestamp}"]
                
                # Format moves with numbers
                formatted_moves = []
                for i, move in enumerate(game.move_history):
                    if i % 2 == 0:
                        formatted_moves.append(f"{i//2 + 1}. {move}")
                    else:
                        formatted_moves.append(move)
                
                if formatted_moves:
                    response.append(" ".join(formatted_moves))
                else:
                    response.append("No moves were made in this game.")
                    
                await ctx.send("\n".join(response))
            except IndexError:
                await ctx.send(f"Game #{game_number} not found! There are {len(past_games)} past games.")
            return
        
        # Show current game
        current_game = channel_data.get('current_game')
        if not current_game:
            await ctx.send("No active game. Use a number to see past games!")
            return
            
        # Format moves with numbers for current game
        formatted_moves = []
        for i, move in enumerate(current_game.move_history):
            if i % 2 == 0:
                formatted_moves.append(f"{i//2 + 1}. {move}")
            else:
                formatted_moves.append(move)
                
        response = ["Current game:"]
        if formatted_moves:
            response.append(" ".join(formatted_moves))
        else:
            response.append("No moves played yet.")
            
        # Add info about viewing past games if they exist
        if channel_data.get('past_games'):
            response.append(f"\nUse `/history <number>` to see past games (1-{len(channel_data['past_games'])})")
            
        await ctx.send("\n".join(response))

    @commands.command()
    async def teams(self, ctx):
        """Show current teams"""
        game = self.bot.get_current_game(ctx.channel.id)
        if not game:
            await ctx.send("No active game in this channel!")
            return
            
        white = game.white_player.name if game.white_player else "Vacant"
        black = game.black_player.name if game.black_player else "Vacant"
        await ctx.send(f"White: {white}\nBlack: {black}")

    @commands.command()
    async def join(self, ctx, color: str):
        """Join as either 'white' or 'black'"""
        game = self.bot.get_current_game(ctx.channel.id)
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
        self.bot.save_games()

    async def send_board(self, ctx):
        """Helper function to send the current board state"""
        game = self.bot.get_current_game(ctx.channel.id)
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

    @commands.command()
    async def save(self, ctx):
        """Manually save all active games"""
        self.bot.save_games()
        await ctx.send("Games saved!")