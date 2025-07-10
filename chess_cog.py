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
        await interaction.response.defer()
        
        game = self.bot.get_current_game(interaction.channel_id)
        if not game:
            await interaction.followup.send("No active game in this channel!")
            return
            
        if game.make_move(move_str):
            await interaction.followup.send(f"Move {move_str} played by {interaction.user.name}!")
            await self.send_board(interaction)
            
            # Check for checkmate or stalemate
            if game.board.is_checkmate():
                winner = "Black" if game.board.turn == chess.WHITE else "White"
                await interaction.followup.send(f"Checkmate! {winner} wins! 🎉")
                await self.stop(interaction)
            elif game.board.is_stalemate():
                await interaction.followup.send("Stalemate! The game is a draw! 🤝")
                await self.stop(interaction)
            else:
                await interaction.followup.send(game.get_next_turn_text())
            
            self.bot.save_games()
        else:
            # Get all legal moves when an invalid move is attempted
            legal_moves = []
            for move in game.board.legal_moves:
                san = game.board.san(move)
                legal_moves.append(san)
            
            legal_moves.sort()
            response = f"`{move_str}` is not a valid move!\n\nLegal moves ({len(legal_moves)}):\n"
            response += ", ".join(legal_moves)
            
            await interaction.followup.send(response)

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

    @app_commands.command(name="history", description="Show move history in PGN and FEN format")
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
                
                response.append("Analyse this position on Lichess:")
                response.append(f"https://lichess.org/analysis/{game.starting_fen.replace(' ', '_')}color=white")
                
                # Format moves with numbers for PGN
                formatted_moves = []
                for i, move in enumerate(game.move_history):
                    if i % 2 == 0:
                        formatted_moves.append(f"{i//2 + 1}. {move}")
                    else:
                        formatted_moves.append(move)
                
                # Add PGN format
                response.append("\n**Use this PGN:**")
                if formatted_moves:
                    response.append("```" + " ".join(formatted_moves) + "```")
                else:
                    response.append("```No moves were made in this game.```")
                    
                await interaction.response.send_message("\n".join(response))
            except IndexError:
                await interaction.response.send_message(f"Game #{game_number} not found! There are {len(past_games)} past games.")
            return
        
        # Show current game
        current_game = channel_data.get('current_game')
        if not current_game:
            await interaction.response.send_message("No active game. Use a number to see past games!")
            return
            
        response = ["**Current game:**"]
        
        # Add starting FEN format
        response.append("Analyse this position on Lichess:")
        response.append(f"https://lichess.org/analysis/{current_game.starting_fen.replace(' ', '_')}color=white")
        
        # Format moves with numbers for PGN
        formatted_moves = []
        for i, move in enumerate(current_game.move_history):
            if i % 2 == 0:
                formatted_moves.append(f"{i//2 + 1}. {move}")
            else:
                formatted_moves.append(move)
            
        # Add PGN format
        response.append("\n**Use this PGN:**")
        if formatted_moves:
            response.append("```" + " ".join(formatted_moves) + "```")
        else:
            response.append("```No moves played yet.```")
            
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

    @app_commands.command(name="assign_player", description="[Admin] Assign a player to a team")
    @app_commands.describe(
        user="The user to assign to a team",
        color="Choose 'white' or 'black'",
        force="Force assignment even if player is already on the other team"
    )
    @app_commands.choices(color=[
        app_commands.Choice(name="White", value="white"),
        app_commands.Choice(name="Black", value="black")
    ])
    @app_commands.default_permissions(manage_guild=True)
    async def assign_player(self, interaction: discord.Interaction, user: discord.Member, color: str, force: bool = False):
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need 'Manage Server' permission to use this command!")
            return
            
        game = self.bot.get_current_game(interaction.channel_id)
        if not game:
            await interaction.response.send_message("No active game in this channel!")
            return
            
        color = color.lower()
        if color not in ['white', 'black']:
            await interaction.response.send_message("Please specify 'white' or 'black'!")
            return
        
        # Check if player is already on a team
        current_team = None
        if user in game.white_players:
            current_team = "white"
        elif user in game.black_players:
            current_team = "black"
        
        # If player is already on the requested team
        if current_team == color:
            await interaction.response.send_message(f"{user.display_name} is already on team {color.title()}!")
            return
        
        # If player is on the other team and force is not used
        if current_team and not force:
            await interaction.response.send_message(
                f"{user.display_name} is already on team {current_team.title()}! "
                f"Use `force: True` to move them to team {color.title()}."
            )
            return
        
        # Remove player from current team if they're on one
        if current_team == "white":
            game.white_players.remove(user)
        elif current_team == "black":
            game.black_players.remove(user)
        
        # Add player to the requested team
        if color == 'white':
            game.white_players.append(user)
            team_name = "White"
        else:
            game.black_players.append(user)
            team_name = "Black"
        
        # Generate response message
        if current_team and force:
            await interaction.response.send_message(
                f"{user.display_name} has been moved from team {current_team.title()} to team {team_name}!"
            )
        else:
            await interaction.response.send_message(
                f"{user.display_name} has been assigned to team {team_name}!"
            )
        
        self.bot.save_games()

    @app_commands.command(name="remove_player", description="[Admin] Remove a player from their team")
    @app_commands.describe(
        user="The user to remove from their team"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def remove_player(self, interaction: discord.Interaction, user: discord.Member):
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need 'Manage Server' permission to use this command!")
            return
            
        game = self.bot.get_current_game(interaction.channel_id)
        if not game:
            await interaction.response.send_message("No active game in this channel!")
            return
        
        # Check if player is on a team
        removed_from = None
        if user in game.white_players:
            game.white_players.remove(user)
            removed_from = "White"
        elif user in game.black_players:
            game.black_players.remove(user)
            removed_from = "Black"
        
        if removed_from:
            await interaction.response.send_message(
                f"{user.display_name} has been removed from team {removed_from}!"
            )
            self.bot.save_games()
        else:
            await interaction.response.send_message(
                f"{user.display_name} is not on any team!"
            )

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
        
        admin_commands = [
            ("assign_player <user> <white/black> [force]", "Assign a player to a team (Admin only)"),
            ("remove_player <user>", "Remove a player from their team (Admin only)"),
            ("reset_teams", "Reset both teams to vacant"),
            ("randomise_teams", "Randomly assign unassigned players to teams (balanced, keeps existing assignments)"),
        ]
        
        help_text = ["**Chess Bot Commands:**"]
        for cmd, desc in commands:
            help_text.append(f"• `/{cmd}` - {desc}")
        
        # Add admin commands if user has permissions
        if interaction.user.guild_permissions.manage_guild:
            help_text.append("\n**Admin Commands:**")
            for cmd, desc in admin_commands:
                help_text.append(f"• `/{cmd}` - {desc}")
            
        await interaction.response.send_message("\n".join(help_text))

    @app_commands.command(name="randomise_teams", description="Randomly assign all players with chess-player role to teams")
    @app_commands.describe(
        include_spectators="Include offline/invisible players (default: True)"
    )
    async def randomise_teams(
        self, 
        interaction: discord.Interaction, 
        include_spectators: bool = True
    ):
        game = self.bot.get_current_game(interaction.channel_id)
        if not game:
            await interaction.response.send_message("No active game in this channel!")
            return

        # Get the chess-player role
        chess_role = discord.utils.get(interaction.guild.roles, name="chess-player")
        if not chess_role:
            await interaction.response.send_message("No 'chess-player' role found in this server!")
            return

        # Get all members with the chess-player role
        eligible_players = [
            member for member in chess_role.members
            if include_spectators or member.status != discord.Status.offline
        ]

        if not eligible_players:
            await interaction.response.send_message("No eligible players found with the 'chess-player' role!")
            return

        # Check if there are existing players on teams
        existing_players = set(game.white_players + game.black_players)
        unassigned_players = [player for player in eligible_players if player not in existing_players]

        import random
        
        if not existing_players:
            # No existing players, clear teams and assign everyone randomly but equally
            game.white_players = []
            game.black_players = []
            players_to_assign = eligible_players
        else:
            # Keep existing teams, only assign unassigned players
            players_to_assign = unassigned_players

        # Assign players to keep teams as equal as possible
        if players_to_assign:
            # Shuffle for randomness
            random.shuffle(players_to_assign)
            
            for player in players_to_assign:
                # Always assign to the smaller team, or randomly if teams are equal
                white_count = len(game.white_players)
                black_count = len(game.black_players)
                
                if white_count < black_count:
                    game.white_players.append(player)
                elif black_count < white_count:
                    game.black_players.append(player)
                else:
                    # Teams are equal, assign randomly
                    if random.choice([True, False]):
                        game.white_players.append(player)
                    else:
                        game.black_players.append(player)

        # Format team lists
        white_team = ", ".join(p.display_name for p in game.white_players) if game.white_players else "No players"
        black_team = ", ".join(p.display_name for p in game.black_players) if game.black_players else "No players"

        # Create appropriate response message
        if not existing_players:
            response = (
                f"Teams have been randomly assigned with balanced distribution!\n\n"
                f"⚪ White Team ({len(game.white_players)} players): {white_team}\n"
                f"⚫ Black Team ({len(game.black_players)} players): {black_team}"
            )
        else:
            if unassigned_players:
                newly_assigned = ", ".join(p.display_name for p in unassigned_players)
                response = (
                    f"Added {len(unassigned_players)} unassigned players to teams with balanced distribution!\n"
                    f"Newly assigned: {newly_assigned}\n\n"
                    f"⚪ White Team ({len(game.white_players)} players): {white_team}\n"
                    f"⚫ Black Team ({len(game.black_players)} players): {black_team}"
                )
            else:
                response = (
                    f"All eligible players are already assigned to teams!\n\n"
                    f"⚪ White Team ({len(game.white_players)} players): {white_team}\n"
                    f"⚫ Black Team ({len(game.black_players)} players): {black_team}"
                )

        await interaction.response.send_message(response)
        self.bot.save_games()

    @commands.command(name="sync")
    @commands.is_owner()  # Only bot owner can use this command
    async def sync(self, ctx):
        """Sync slash commands to the current guild"""
        try:
            synced = await ctx.bot.tree.sync()
            await ctx.send(f"Synced {len(synced)} commands!")
        except Exception as e:
            await ctx.send(f"Failed to sync commands: {str(e)}")

    @app_commands.command(name="legal", description="Show all legal moves in the current position")
    async def legal_moves(self, interaction: discord.Interaction):
        game = self.bot.get_current_game(interaction.channel_id)
        if not game:
            await interaction.response.send_message("No active game in this channel!")
            return
        
        # Get all legal moves in SAN notation
        legal_moves = []
        for move in game.board.legal_moves:
            san = game.board.san(move)
            legal_moves.append(san)
        
        # Sort moves for readability
        legal_moves.sort()
        
        # Format the response
        response = f"Legal moves ({len(legal_moves)}):\n"
        response += ", ".join(legal_moves)
        
        await interaction.response.send_message(response)

    @app_commands.command(name="castling", description="Show or modify castling rights")
    @app_commands.describe(
        action="View or reset castling rights",
        side="Which side to modify (optional)",
        wing="Which wing to modify (optional)"
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="view", value="view"),
            app_commands.Choice(name="reset", value="reset")
        ],
        side=[
            app_commands.Choice(name="white", value="white"),
            app_commands.Choice(name="black", value="black")
        ],
        wing=[
            app_commands.Choice(name="kingside", value="kingside"),
            app_commands.Choice(name="queenside", value="queenside"),
            app_commands.Choice(name="both", value="both")
        ]
    )
    async def castling_rights(
        self, 
        interaction: discord.Interaction, 
        action: str = "view",
        side: str = None,
        wing: str = None
    ):
        game = self.bot.get_current_game(interaction.channel_id)
        if not game:
            await interaction.response.send_message("No active game in this channel!")
            return

        if action == "view":
            rights = game.get_castling_rights()
            variant = "Chess960" if game.is_960 else "Standard"
            response = f"{variant} game\n{rights}"
            await interaction.response.send_message(response)
            return

        # Handle reset action
        if not side and not wing:
            # Reset all castling rights
            game.reset_castling_rights(chess.WHITE, "kingside")
            game.reset_castling_rights(chess.WHITE, "queenside")
            game.reset_castling_rights(chess.BLACK, "kingside")
            game.reset_castling_rights(chess.BLACK, "queenside")
            message = "Reset all castling rights"
        elif side and not wing:
            # Reset both wings for specified side
            color = chess.WHITE if side == "white" else chess.BLACK
            game.reset_castling_rights(color, "kingside")
            game.reset_castling_rights(color, "queenside")
            message = f"Reset all castling rights for {side}"
        elif side and wing:
            # Reset specific wing for specific side
            color = chess.WHITE if side == "white" else chess.BLACK
            if wing == "both":
                game.reset_castling_rights(color, "kingside")
                game.reset_castling_rights(color, "queenside")
                message = f"Reset both castling rights for {side}"
            else:
                game.reset_castling_rights(color, wing)
                message = f"Reset {wing} castling rights for {side}"
        else:  # wing but no side
            # Reset specified wing for both sides
            game.reset_castling_rights(chess.WHITE, wing)
            game.reset_castling_rights(chess.BLACK, wing)
            message = f"Reset {wing} castling rights for both sides"

        # Show updated rights
        rights = game.get_castling_rights()
        response = f"{message}\nUpdated castling rights:\n{rights}"
        await interaction.response.send_message(response)