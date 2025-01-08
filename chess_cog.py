import discord
from discord.ext import commands
import chess
import datetime
import chess.svg
from chess_game import ChessGame
from discord import app_commands

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

    @app_commands.command(name="start", description="Start a new chess game")
    @app_commands.describe(
        variant="Use '960' for Chess960 variant",
        fen="Provide a custom FEN position"
    )
    async def start(self, interaction: discord.Interaction, variant: str = None, fen: str = None):
        channel_id = interaction.channel_id
        
        if channel_id in self.bot.channel_data and self.bot.channel_data[channel_id].get('current_game'):
            await interaction.response.send_message("There's already an active game! Use `/stop` to end it first.")
            return
        
        # Handle Chess960 variant
        is_960 = variant == '960'
        
        # Create new game with no players assigned
        game = ChessGame(variant_960=is_960)
        game.timestamp = datetime.datetime.now().isoformat()
        
        # Handle custom FEN if provided (and not Chess960)
        if fen and not is_960:
            try:
                game.board.set_fen(fen)
            except:
                await interaction.response.send_message("Invalid FEN position!")
                return
        
        if channel_id not in self.bot.channel_data:
            self.bot.channel_data[channel_id] = {
                'current_game': None,
                'past_games': []
            }
        
        self.bot.channel_data[channel_id]['current_game'] = game
        
        # Customize message based on variant
        variant_msg = "chess960" if is_960 else "chess"
        await interaction.response.send_message(f"New {variant_msg} game started! Use `/join white` or `/join black` to play!")
        await self.send_board(interaction)
        self.bot.save_games()

    @app_commands.command(name="stop", description="Stop the current game and save it to history")
    async def stop(self, interaction: discord.Interaction):
        channel_id = interaction.channel_id
        
        if channel_id not in self.bot.channel_data or not self.bot.channel_data[channel_id].get('current_game'):
            await interaction.response.send_message("No active game to stop!")
            return
        
        # Archive the current game (keeping player assignments)
        current_game = self.bot.channel_data[channel_id]['current_game']
        current_game.completed = True
        current_game.timestamp = datetime.datetime.now().isoformat()
        
        if 'past_games' not in self.bot.channel_data[channel_id]:
            self.bot.channel_data[channel_id]['past_games'] = []
        
        self.bot.channel_data[channel_id]['past_games'].append(current_game)
        self.bot.channel_data[channel_id]['current_game'] = None
        
        await interaction.response.send_message("Game stopped and saved to history!")
        self.bot.save_games()

    @app_commands.command(name="current", description="Show the current game status")
    async def show_current(self, interaction: discord.Interaction):
        game = self.bot.get_current_game(interaction.channel_id)
        if not game:
            await interaction.response.send_message("No active game in this channel!")
            return
        
        status = game.get_current_status()
        await interaction.response.send_message("\n".join(status))
        await self.send_board(interaction)

    @app_commands.command(name="move", description="Make a move using algebraic notation")
    @app_commands.describe(move_str="The move in algebraic notation (e.g., e4, Nf3)")
    async def move(self, interaction: discord.Interaction, move_str: str):
        game = self.bot.get_current_game(interaction.channel_id)
        if not game:
            await interaction.response.send_message("No active game in this channel!")
            return
        
        # Check if it's the right player's turn
        current_players = game.white_players if game.board.turn == chess.WHITE else game.black_players
        if interaction.user not in current_players:
            if not current_players:
                color = "White" if game.board.turn == chess.WHITE else "Black"
                await interaction.response.send_message(f"The {color} team is vacant! Join with `/join {color.lower()}`")
            else:
                await interaction.response.send_message(f"It's not your turn! Waiting for {game.get_next_turn_text()}")
            return
            
        if game.make_move(move_str):
            await interaction.response.send_message(f"Move {move_str} played!")
            await self.send_board(interaction)
            
            # Check for checkmate or stalemate
            if game.board.is_checkmate():
                winner = "Black" if game.board.turn == chess.WHITE else "White"
                await interaction.response.send_message(f"Checkmate! {winner} wins! 🎉")
                await self.stop(interaction)
            elif game.board.is_stalemate():
                await interaction.response.send_message("Stalemate! The game is a draw! 🤝")
                await self.stop(interaction)
            else:
                await interaction.response.send_message(game.get_next_turn_text())
            
            self.bot.save_games()
        else:
            await interaction.response.send_message(f"{move_str} is not a valid move!")

    @app_commands.command(name="undo", description="Undo the last move")
    async def undo(self, interaction: discord.Interaction):
        game = self.bot.get_current_game(interaction.channel_id)
        if not game:
            await interaction.response.send_message("No active game in this channel!")
            return
            
        move = game.undo_move()
        if move:
            await interaction.response.send_message(f"Move {move} undone!")
            await self.send_board(interaction)
        else:
            await interaction.response.send_message("No moves to undo!")

    @app_commands.command(name="history", description="Show move history")
    @app_commands.describe(game_number="Optional: View a specific past game")
    async def history(self, interaction: discord.Interaction, game_number: int = None):
        channel_id = interaction.channel_id
        if channel_id not in self.bot.channel_data:
            await interaction.response.send_message("No games have been played in this channel!")
            return
            
        channel_data = self.bot.channel_data[channel_id]
        
        if game_number is not None:
            # Show past game
            past_games = channel_data.get('past_games', [])
            if not past_games:
                await interaction.response.send_message("No past games found!")
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
                    
                await interaction.response.send_message("\n".join(response))
            except IndexError:
                await interaction.response.send_message(f"Game #{game_number} not found! There are {len(past_games)} past games.")
            return
        
        # Show current game
        current_game = channel_data.get('current_game')
        if not current_game:
            await interaction.response.send_message("No active game. Use a number to see past games!")
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
            
        await interaction.response.send_message("\n".join(response))

    @app_commands.command(name="teams", description="Show current teams")
    async def teams(self, interaction: discord.Interaction):
        game = self.bot.get_current_game(interaction.channel_id)
        if not game:
            await interaction.response.send_message("No active game in this channel!")
            return
            
        white = ", ".join(p.name for p in game.white_players) if game.white_players else "Vacant"
        black = ", ".join(p.name for p in game.black_players) if game.black_players else "Vacant"
        await interaction.response.send_message(f"White: {white}\nBlack: {black}")

    @app_commands.command(name="join", description="Join as either white or black")
    @app_commands.describe(color="Choose 'white' or 'black'")
    @app_commands.choices(color=[
        app_commands.Choice(name="White", value="white"),
        app_commands.Choice(name="Black", value="black")
    ])
    async def join(self, interaction: discord.Interaction, color: str):
        game = self.bot.get_current_game(interaction.channel_id)
        if not game:
            await interaction.response.send_message("No active game in this channel!")
            return
            
        color = color.lower()
        if color not in ['white', 'black']:
            await interaction.response.send_message("Please specify 'white' or 'black'!")
            return
        
        # Check if player is already on either team
        if interaction.user in game.white_players:
            await interaction.response.send_message("You're already playing as White! Use `/leave` first to switch teams.")
            return
        if interaction.user in game.black_players:
            await interaction.response.send_message("You're already playing as Black! Use `/leave` first to switch teams.")
            return
            
        if color == 'white':
            game.white_players.append(interaction.user)
            await interaction.response.send_message(f"{interaction.user.name} has joined team White!")
        else:
            game.black_players.append(interaction.user)
            await interaction.response.send_message(f"{interaction.user.name} has joined team Black!")
        self.bot.save_games()

    @app_commands.command(name="leave", description="Leave your current team")
    async def leave(self, interaction: discord.Interaction):
        game = self.bot.get_current_game(interaction.channel_id)
        if not game:
            await interaction.response.send_message("No active game in this channel!")
            return
            
        if interaction.user in game.white_players:
            game.white_players.remove(interaction.user)
            await interaction.response.send_message(f"{interaction.user.name} has left the white team!")
        elif interaction.user in game.black_players:
            game.black_players.remove(interaction.user)
            await interaction.response.send_message(f"{interaction.user.name} has left the black team!")
        else:
            await interaction.response.send_message("You're not on any team!")
        
        self.bot.save_games()

    @app_commands.command(name="reset_teams", description="Reset both teams to vacant")
    async def reset_teams(self, interaction: discord.Interaction):
        game = self.bot.get_current_game(interaction.channel_id)
        if not game:
            await interaction.response.send_message("No active game in this channel!")
            return
            
        game.white_players = []
        game.black_players = []
        await interaction.response.send_message("Teams have been reset! Both sides are now vacant.")
        self.bot.save_games()

    @app_commands.command(name="save", description="Manually save all active games")
    async def save(self, interaction: discord.Interaction):
        self.bot.save_games()
        await interaction.response.send_message("Games saved!")

    @app_commands.command(name="advice", description="Get some questionably useful chess advice")
    async def advice(self, interaction: discord.Interaction):
        """Get some questionably useful chess advice"""
        import random
        
        if random.random() < 0.3:
            advice = random.choice(self.generic_advice)
        else:
            piece = random.choice(list(self.piece_types.keys()))
            direction = random.choice(self.directions)
            advice = f"{self.piece_types[piece]} {direction}."
        await interaction.response.send_message(f"🧙‍♂️ Chess Wisdom: {advice}")

    # Helper method needs to be updated to work with interactions
    async def send_board(self, interaction):
        """Helper function to send the current board state"""
        game = self.bot.get_current_game(interaction.channel_id)
        if game:
            board_image = game.get_board_image()
            await interaction.followup.send(file=discord.File(board_image, 'board.png'))

    @app_commands.command(name="help", description="Show all available chess commands")
    async def help(self, interaction: discord.Interaction):
        commands = [
            ("start [960] [fen]", "Start a new chess game. Use '960' for Chess960 variant, or provide a FEN position"),
            ("stop", "Stop the current game and save it to history"),
            ("move <move>", "Make a move using algebraic notation (e.g., e4, Nf3)"),
            ("join <white/black>", "Join a team"),
            ("leave", "Leave your current team"),
            ("teams", "Show current teams"),
            ("current", "Show the current game status"),
            ("history [game_number]", "Show move history. Optionally view a past game"),
            ("advice", "Get some questionably useful chess advice"),
        ]
        
        help_text = ["**Chess Bot Commands:**"]
        for cmd, desc in commands:
            help_text.append(f"• `/{cmd}` - {desc}")
            
        await interaction.response.send_message("\n".join(help_text))